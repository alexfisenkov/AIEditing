"""Design layer as pictures: chapter plates, captions, cards and variants on a person's frame.

Pillow is needed only when something is drawn; importing this package never requires it.
"""
from .design import default_design, load_design, variants
from .errors import RenderError
from .place import opposite_corner
from .plate import plate
from .samples import samples

__all__ = ["RenderError", "default_design", "load_design", "opposite_corner", "plate", "samples",
           "variants"]
