"""Store stream sectors in the physical 1,9,2,10,... TR-DOS track order."""


def physical_sector(logical):
    return (logical >> 1) + (8 if logical & 1 else 0)


def positions(sectors: int, first_sector: int):
    if sectors < 0 or not 0 <= first_sector < 16:
        raise ValueError('invalid sector count or initial sector')
    for index in range(sectors):
        track, sector = divmod(first_sector + index, 16)
        yield track*16 + (physical_sector(sector) if track else sector) - first_sector


def required_sectors(sectors: int, first_sector: int) -> int:
    """Include holes at the end of the last, partially occupied track."""
    return max(positions(sectors, first_sector), default=-1) + 1


def arrange(video: bytes, first_sector: int) -> bytes:
    if len(video) % 256:
        raise ValueError('stream must be sector-aligned')
    result=bytearray(required_sectors(len(video)//256, first_sector)*256)
    for index,physical in enumerate(positions(len(video)//256, first_sector)):
        result[physical*256:(physical+1)*256]=video[index*256:(index+1)*256]
    return bytes(result)
