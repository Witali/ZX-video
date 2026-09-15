"""Seek known 80-track double-sided media without TR-DOS READ ADDRESS.

The first read still initializes the drive through C=5. Later seeks use the
tested 5.03 ROM's side selectors and Type-I command wrapper. Sector IDs remain
checked by the read command. E=1 requests controller head settling after seek.
"""
import playback_schedule


def emit(a):
    a.label('seek_cached_track')
    a.emit(0xE5,0x7A,0x32);a.word(0x5CF5)
    a.abs16(0x32,'fast_disk_track')
    playback_schedule.select_rom_clock(a,True)
    a.abs16(0x3A,'disk_track');a.emit(0xE6,1,0x11);a.word(0x1FEB)
    a.rel8(0x28,'seek_side_ready');a.emit(0x11);a.word(0x1FF6)
    a.label('seek_side_ready')
    a.abs16(0x21,'seek_side_return');a.emit(0xE5,0xD5)
    a.emit(0x3E,0xBE,0xED,0x47,0xED,0x5E,0xFB)
    a.label('seek_side_enter');a.emit(0xC3);a.word(0x3D2F)
    a.label('seek_side_return');a.emit(0xF3)
    # Retain the drive's configured step-rate bits. The ROM wrapper adds 18h
    # (SEEK + head load), waits for INTRQ and supports its usual BREAK check.
    a.emit(0x3A);a.word(0x5CF6);a.emit(0x5F,0x16,0,0x21);a.word(0x5CFA)
    a.emit(0x19,0x7E,0xE6,3,0x47)
    a.abs16(0x3A,'disk_track');a.emit(0xCB,0x3F)
    a.abs16(0x21,'seek_return');a.emit(0xE5,0x21);a.word(0x3E44)
    a.emit(0xE5,0xFB)
    a.label('seek_enter');a.emit(0xC3);a.word(0x3D2F)
    a.label('seek_return');a.emit(0xF3)
    playback_schedule.select_rom_clock(a,False)
    a.emit(0x3E,0x84,0x32);a.word(0x5CFE)
    a.emit(0xE1,0xC9)
