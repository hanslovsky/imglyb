import logging
import sys

_logger = logging.getLogger(__name__)

__all__ = ('to_imglib', 'to_imglib_argb', 'to_numpy')

def _init_jvm_options():
    from .config import get_imglib2_imglyb_version
    import jpype
    import scyjava.config

    imglib2_imglyb_version = get_imglib2_imglyb_version()

    if scyjava.config.jvm_status():
        _logger.warning('JVM is already running, will not add relevant endpoints to classpath -- '
                        'required classes might not be on classpath. '
                        'In case of failure, try importing imglyb before scyjava or jpype')

    IMGLIB2_IMGLYB_ENDPOINT = 'net.imglib2:imglib2-imglyb:{}'.format(imglib2_imglyb_version)
    RELEVANT_MAVEN_REPOS    = {
        'scijava.public' : scyjava.config.maven_scijava_repository()
    }
    for _, repo in scyjava.config.get_repositories().items():
        if 'scijava.public' in RELEVANT_MAVEN_REPOS and repo == RELEVANT_MAVEN_REPOS['scijava.public']:
            del RELEVANT_MAVEN_REPOS['scijava.public']
    scyjava.config.add_repositories(RELEVANT_MAVEN_REPOS)
    scyjava.config.add_endpoints(IMGLIB2_IMGLYB_ENDPOINT)

    import scyjava

    return

from .imglib_ndarray import ImgLibReferenceGuard as _ImgLibReferenceGuard
from .ndarray_like_as_img import \
    as_cell_img, \
    as_cell_img_with_array_accesses, \
    as_cell_img_with_native_accesses
from .util import \
    to_imglib, \
    to_imglib_argb


def to_numpy(source):
    return _ImgLibReferenceGuard(source)
