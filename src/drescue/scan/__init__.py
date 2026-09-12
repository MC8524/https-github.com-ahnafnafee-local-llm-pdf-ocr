"""Structure discovery: partition tables, filesystem identification, carving."""

from .partitions import Partition, PartitionTable, read_partitions
from .filesystems import FilesystemInfo, identify_filesystem, find_lost_filesystems

__all__ = [
    "Partition",
    "PartitionTable",
    "read_partitions",
    "FilesystemInfo",
    "identify_filesystem",
    "find_lost_filesystems",
]
