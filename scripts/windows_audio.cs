// Accès aux points de terminaison audio Windows (Core Audio, COM) pour lister et renommer
// le micro virtuel VB-CABLE. Chargé par les scripts PowerShell via Add-Type.
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

namespace AbyssSetup
{
    [StructLayout(LayoutKind.Sequential)]
    public struct PropertyKey { public Guid fmtid; public int pid; }

    [StructLayout(LayoutKind.Explicit, Size = 16)]
    public struct PropVariant { [FieldOffset(0)] public ushort vt; [FieldOffset(8)] public IntPtr ptr; }

    [ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore
    {
        [PreserveSig] int GetCount(out int count);
        [PreserveSig] int GetAt(int index, out PropertyKey key);
        [PreserveSig] int GetValue(ref PropertyKey key, out PropVariant value);
        [PreserveSig] int SetValue(ref PropertyKey key, ref PropVariant value);
        [PreserveSig] int Commit();
    }

    [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice
    {
        [PreserveSig] int Activate(ref Guid iid, int context, IntPtr parameters, [MarshalAs(UnmanagedType.IUnknown)] out object iface);
        [PreserveSig] int OpenPropertyStore(int access, out IPropertyStore store);
        [PreserveSig] int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
        [PreserveSig] int GetState(out int state);
    }

    [ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceCollection
    {
        [PreserveSig] int GetCount(out int count);
        [PreserveSig] int Item(int index, out IMMDevice device);
    }

    [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator
    {
        [PreserveSig] int EnumAudioEndpoints(int dataFlow, int stateMask, out IMMDeviceCollection devices);
    }

    [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
    class MMDeviceEnumerator { }

    public static class Endpoints
    {
        const int CAPTURE = 1;          // eCapture
        const int ACTIVE = 1;           // DEVICE_STATE_ACTIVE
        const int STGM_READ = 0, STGM_READWRITE = 2;
        const ushort VT_LPWSTR = 31;
        // PKEY_Device_DeviceDesc : nom court du point de terminaison (« CABLE Output »)
        static PropertyKey DeviceDesc = new PropertyKey { fmtid = new Guid("a45c254e-df1c-4efd-8020-67d146a850e0"), pid = 2 };
        // PKEY_DeviceInterface_FriendlyName : nom du pilote (« VB-Audio Virtual Cable »)
        static PropertyKey InterfaceName = new PropertyKey { fmtid = new Guid("026e516e-b814-414b-83cd-856d6fef4822"), pid = 2 };

        static string Read(IPropertyStore store, PropertyKey key)
        {
            PropVariant v;
            if (store.GetValue(ref key, out v) != 0 || v.vt != VT_LPWSTR || v.ptr == IntPtr.Zero) return "";
            return Marshal.PtrToStringUni(v.ptr);
        }

        static IEnumerable<IMMDevice> Captures()
        {
            var enumerator = (IMMDeviceEnumerator)new MMDeviceEnumerator();
            IMMDeviceCollection devices;
            Marshal.ThrowExceptionForHR(enumerator.EnumAudioEndpoints(CAPTURE, ACTIVE, out devices));
            int count;
            devices.GetCount(out count);
            for (int i = 0; i < count; i++) { IMMDevice d; devices.Item(i, out d); yield return d; }
        }

        /// <summary>Micros actifs : « nom|pilote » pour chacun.</summary>
        public static List<string> ListCaptures()
        {
            var result = new List<string>();
            foreach (var d in Captures())
            {
                IPropertyStore store;
                if (d.OpenPropertyStore(STGM_READ, out store) != 0) continue;
                result.Add(Read(store, DeviceDesc) + "|" + Read(store, InterfaceName));
            }
            return result;
        }

        /// <summary>Renomme le micro du pilote VB-CABLE. → "renamed", "already" ou "notfound". Nécessite les droits admin.</summary>
        public static string RenameCable(string newName)
        {
            foreach (var d in Captures())
            {
                IPropertyStore store;
                if (d.OpenPropertyStore(STGM_READ, out store) != 0) continue;
                if (Read(store, InterfaceName).IndexOf("VB-Audio Virtual Cable", StringComparison.OrdinalIgnoreCase) < 0) continue;
                if (Read(store, DeviceDesc) == newName) return "already";
                IPropertyStore writable;
                Marshal.ThrowExceptionForHR(d.OpenPropertyStore(STGM_READWRITE, out writable));
                var value = new PropVariant { vt = VT_LPWSTR, ptr = Marshal.StringToCoTaskMemUni(newName) };
                try
                {
                    Marshal.ThrowExceptionForHR(writable.SetValue(ref DeviceDesc, ref value));
                    writable.Commit();
                }
                finally { Marshal.FreeCoTaskMem(value.ptr); }
                return "renamed";
            }
            return "notfound";
        }
    }
}
