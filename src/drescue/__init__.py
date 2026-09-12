"""drescue — block-level data recovery imaging, scanning and carving.

Three commands, one library:

* ``rescue``  — fault-tolerant imaging with a GNU ddrescue-compatible mapfile
                (copy → trim → scrape → retry), resumable and interruptible.
* ``scan``    — partition tables (MBR/GPT) and filesystem identification on a
                device or a partial image.
* ``carve``   — signature-based file recovery that is *mapfile aware*: files
                overlapping unrecovered sectors are reported as suspect.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
