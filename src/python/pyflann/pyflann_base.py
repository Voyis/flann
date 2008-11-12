
from util.weave_tools import *
from pyflann_parameters import *
import os

DEBUG = False

def find_root(directory = None):
    if directory == None:
        directory = os.path.dirname(__file__)
    if os.path.isfile(directory+"/flann.py"):
        return os.path.abspath(directory+"/..")
    else:
        return find_root(os.path.abspath(directory+"/.."))

root_dir = find_root()

module = CModule()
module.include('"flann.h"')

module.customize.add_include_dir(root_dir+'/include')
module.customize.add_include_dir(root_dir+'/cpp')
module.customize.add_library('flann')
module.customize.add_library_dir(root_dir+'/lib')
module.customize.add_library_dir(root_dir+'/python')



if DEBUG:
    module.customize.add_extra_compile_arg('-g')
else:
    module.customize.add_extra_compile_arg('-O3')


flannparam_set_code = \
    ("FLANNParameters flannparams;\n"
    + ''.join(['flannparams.%s = %s; \n' % (n, n)
                for n in get_flann_param_struct_name_list()])
        #+ r"""
        #if(log_destination.size() == 0) flannparams.log_destination = NULL;
        #else flannparams.log_destination = log_destination.c_str();
        #"""
    + r"flannparams.log_destination = NULL;"
    )

flannparam_ptr_code = r"&flannparams"

idxparam_set_code = \
    ("IndexParameters idxparams;\n"
    + ''.join(['idxparams.%s = %s; \n' % (n, n)
                for n in get_index_param_struct_name_list()])
    )
        
ret_params_code = \
    ("py::dict ret_params;\n"
    + ''.join(['ret_params["%s"] = idxparams.%s; \n'
                % (n, n) for n in get_index_param_struct_name_list()])
    )

idxparam_ptr_code = r"&idxparams"

param_set_code = flannparam_set_code + idxparam_set_code


        
        
@module
def flatten_double2float(pts = float64_2d, pts_flat = float32_2d):
    r"""
    size_t loc = 0;
    for(int i = 0; i < Npts[0]; ++i)
    {
        for(int p = 0; p < Npts[1]; ++p)
        {
        pts_flat[loc] = float( PTS2(i,p) );
        ++loc;
        }
    }
    """
        
@module.extra_args(*get_param_compile_args())
def build_index(dataset = float32_2d, npts = int(0), dim = int(0)):
    return param_set_code + r'''
            float speedup = 1;
            py::tuple result(2);
            result[0] = flann_build_index(dataset, npts, dim, &speedup, %s, %s);
            ''' % (idxparam_ptr_code, flannparam_ptr_code) + \
            ret_params_code + r'''
            ret_params["speedup"] = speedup;
            result[1] = ret_params;
            return_val = result;
            '''

@module.extra_args(*get_flann_param_compile_args())
def free_index(index = int(0)):
    return flannparam_set_code + r'''
            flann_free_index(FLANN_INDEX(index), %s);
            ''' % flannparam_ptr_code
 
 
@module.extra_args(*get_param_compile_args())
def find_nearest_neighbors(dataset = float32_2d, npts = int(0), dim = int(0), testset = float32_2d, tcount = int(0), result = int32_2d, num_neighbors = int(0)): 
    return param_set_code + r'''
            //printf("npts = %%d, dim = %%d, tcount = %%d\n", npts, dim, tcount);
            flann_find_nearest_neighbors(dataset, npts, dim, testset, tcount,
            (int*)result, num_neighbors, %s, %s);
            ''' % (idxparam_ptr_code, flannparam_ptr_code)
            

@module.extra_args(*get_flann_param_compile_args())
def find_nearest_neighbors_index(index = int(0), testset = float32_2d, tcount = int(0), result = int32_2d, num_neighbors=int(0), checks = int(0)):
    return flannparam_set_code + r"""
            flann_find_nearest_neighbors_index(FLANN_INDEX(index), testset, tcount,
            (int*)result, num_neighbors, checks, %s);
            """ % flannparam_ptr_code
            
@module.extra_args(*get_param_compile_args())
def run_kmeans(dataset = float32_2d, npts = int(0), dim = int(0), num_clusters = int(0), result = float32_2d):
    return param_set_code + """
            return_val = flann_compute_cluster_centers(dataset, npts, dim, num_clusters, (float*)result, %s, %s);
            """ % (idxparam_ptr_code, flannparam_ptr_code)


module.customize.add_include_dir(root_dir+"/cpp/algorithms")
module.customize.add_include_dir(root_dir+"/cpp/nn")
module.customize.add_include_dir(root_dir+"/cpp/util")
module.include('"ground_truth.h"')

@module
def compute_ground_truth_float(dataset = float32_2d, testset = float32_2d, match = int32_2d, skip = int(0)):
    r'''
    Dataset<float> _dataset(Ndataset[0], Ndataset[1], dataset);
    Dataset<float> _testset(Ntestset[0], Ntestset[1], testset);
    Dataset<int> _match(Nmatch[0], Nmatch[1], (int*) match);
    compute_ground_truth(_dataset, _testset, _match, skip);
    '''



import_str = module._import(verbose=2)
exec import_str