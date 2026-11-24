"""Read only the effective token identities needed to keep a private directory usable."""
import ctypes
from ctypes import wintypes


def private_sids(user, logon_sids, restricted_sids, appcontainer):
    # Never turn arbitrary token groups (Users/Everyone/capabilities) into grants.
    allowed = {user, 'S-1-5-18'}
    if appcontainer:
        if not appcontainer.startswith('S-1-15-2-'):
            raise ValueError('unsupported container identity')
        allowed.add(appcontainer)
    for sid in restricted_sids:
        if sid in logon_sids and sid.startswith('S-1-5-5-'):
            allowed.add(sid)
    # A restricting SID may satisfy the second access check without granting every SID.
    # Keep the grants unchanged; DACL verification and the actual IO probe remain mandatory.
    if restricted_sids and set(restricted_sids).isdisjoint(allowed):
        raise ValueError('unsupported restricted identity')
    return sorted(allowed)


def current_private_identity():
    """Use the thread token when impersonating; never read credentials or log SIDs."""
    class SidAndAttributes(ctypes.Structure):
        _fields_ = [('sid', ctypes.c_void_p), ('attributes', wintypes.DWORD)]
    class Groups(ctypes.Structure):
        _fields_ = [('count', wintypes.DWORD), ('groups', SidAndAttributes * 1)]

    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    for name in ('GetCurrentProcess', 'GetCurrentThread'):
        getattr(kernel, name).restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    advapi.OpenThreadToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    token = wintypes.HANDLE()
    if not advapi.OpenThreadToken(kernel.GetCurrentThread(), 8, True, ctypes.byref(token)):
        error = ctypes.get_last_error()
        if error != 1008:  # ERROR_NO_TOKEN is the only process-token fallback.
            raise ctypes.WinError(error)
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
            raise ctypes.WinError(ctypes.get_last_error())
    try:
        def info(kind):
            length = wintypes.DWORD()
            advapi.GetTokenInformation(token, kind, None, 0, ctypes.byref(length))
            if ctypes.get_last_error() != 122 or not length.value:
                raise ctypes.WinError(ctypes.get_last_error())
            buffer = ctypes.create_string_buffer(length.value)
            if not advapi.GetTokenInformation(token, kind, buffer, length, ctypes.byref(length)):
                raise ctypes.WinError(ctypes.get_last_error())
            return buffer

        def sid_string(pointer):
            if not pointer:
                return None
            output = ctypes.c_void_p()
            if not advapi.ConvertSidToStringSidW(pointer, ctypes.byref(output)):
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                return ctypes.wstring_at(output)
            finally:
                kernel.LocalFree(output)

        def groups(kind):
            buffer = info(kind)
            count = wintypes.DWORD.from_buffer(buffer).value
            if not count:
                return []
            entries = (SidAndAttributes * count).from_buffer(buffer, Groups.groups.offset)
            return [(sid_string(item.sid), item.attributes) for item in entries]

        user_buffer = info(1)  # TokenUser
        user = sid_string(SidAndAttributes.from_buffer(user_buffer).sid)
        logons = {sid for sid, flags in groups(2) if flags & 0xC0000000 == 0xC0000000}
        restricted = [sid for sid, _ in groups(11)]
        container_buffer = info(31)  # TokenAppContainerSid
        container = sid_string(ctypes.c_void_p.from_buffer(container_buffer).value)
        return user, private_sids(user, logons, restricted, container)
    finally:
        kernel.CloseHandle(token)
