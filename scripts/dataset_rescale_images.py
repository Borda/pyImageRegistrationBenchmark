"""
Converting images to particular scales

With given path pattern to images crete particular scales within the same set

Note, for the loading we have to use matplotlib while ImageMagic nor other lib
(opencv, skimage, Pillow) is able to load larger images then 32k.
On the other hand matplotlib is not able to save such large image.

EXAMPLE
-------
>> python dataset_rescale_images.py \
    -i "/datagrid/Medical/dataset_ANHIR/images/COAD_*/scale-100pc/*.png" \
    --scales 5 10 25 50 --nb_jobs 4

Copyright (C) 2016-2018 Jiri Borovec <jiri.borovec@fel.cvut.cz>
"""

import os
import sys
import glob
import time
import gc
import re
import logging
import argparse
import multiprocessing as mproc
from functools import partial

from skimage.transform import rescale

sys.path += [os.path.abspath('.'), os.path.abspath('..')]  # Add path to root
from benchmark.utilities.experiments import wrap_execute_sequence
from benchmark.utilities.dataset import load_large_image, save_large_image

NB_THREADS = int(mproc.cpu_count() * .5)
DEFAULT_SCALES = [5, 10, 25, 50]
IMAGE_EXTENSION = '.jpg'
FOLDER_TEMPLATE = 'scale-%ipc'


def arg_parse_params():
    """ parse the input parameters
    :return dict: {str: any}
    """
    # SEE: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--path_images', type=str, required=True,
                        help='path (pattern) to the input image')
    parser.add_argument('--scales', type=int, required=False, nargs='+',
                        help='list of output scales', default=DEFAULT_SCALES)
    parser.add_argument('--overwrite', action='store_true', required=False,
                        default=False, help='visualise the landmarks in images')
    parser.add_argument('--nb_jobs', type=int, required=False,
                        help='number of processes running in parallel',
                        default=NB_THREADS)
    args = vars(parser.parse_args())
    args['path_images'] = os.path.expanduser(args['path_images'])
    if not isinstance(args['scales'], list):
        args['scales'] = [args['scales']]
    logging.info('ARGUMENTS: \n%s' % repr(args))
    return args


def scale_image(img_path, scale, overwrite=False):
    base = os.path.dirname(os.path.dirname(img_path))
    name = os.path.splitext(os.path.basename(img_path))[0]
    dir = os.path.basename(os.path.dirname(img_path))
    base_scale = int(re.findall('\d+', dir)[0])

    path_dir = os.path.join(base, FOLDER_TEMPLATE % scale)
    if not os.path.isdir(path_dir):
        os.mkdir(path_dir)

    path_img_scale = os.path.join(path_dir, name + IMAGE_EXTENSION)
    if os.path.isfile(path_img_scale) and not overwrite:
        logging.debug('existing "%s"', path_img_scale)
        return

    img = load_large_image(img_path)
    order = 1 if base_scale > scale else 2
    img_sc = rescale(img, scale / float(base_scale), order=order,
                     anti_aliasing=True, mode='constant', multichannel=True)
    del img
    logging.debug('creating >> %s', path_img_scale)
    save_large_image(path_img_scale, img_sc)
    gc.collect(), time.sleep(1)


def wrap_scale_image(img_path_scale, overwrite=False):
    img_path, scale = img_path_scale
    return scale_image(img_path, scale, overwrite)


def main(path_images, scales, overwrite, nb_jobs):
    image_paths = sorted(glob.glob(path_images))
    image_path_scales = [(im_path, sc) for im_path in image_paths
                         for sc in scales]

    _wrap_scale = partial(wrap_scale_image, overwrite=overwrite)
    list(wrap_execute_sequence(_wrap_scale, image_path_scales,
                               desc='scaling images', nb_jobs=nb_jobs))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    arg_params = arg_parse_params()
    main(arg_params['path_images'], arg_params['scales'],
         arg_params['overwrite'], arg_params['nb_jobs'])

    logging.info('DONE')