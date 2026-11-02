# Read only default multimedia output peak meters; no recording, names or settings.
# https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nn-endpointvolume-iaudiometerinformation
param([ValidateRange(1,60)][int]$Seconds=10)
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
[ComImport,Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class PeakDeviceEnumerator {}
[ComImport,Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IPeakEnumerator {
 [PreserveSig] int EnumAudioEndpoints(int flow,uint mask,out IntPtr devices);
 [PreserveSig] int GetDefaultAudioEndpoint(int flow,int role,out IPeakDevice device);
}
[ComImport,Guid("D666063F-1587-4E43-81F1-B948E807363F"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IPeakDevice {
 [PreserveSig] int Activate(ref Guid iid,uint context,IntPtr parameters,[MarshalAs(UnmanagedType.IUnknown)] out object result);
}
[ComImport,Guid("C02216F6-8C67-4B5B-9D00-D008E73E0064"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IPeakMeter {
 [PreserveSig] int GetPeakValue(out float value);
 [PreserveSig] int GetMeteringChannelCount(out uint count);
 [PreserveSig] int GetChannelsPeakValues(uint count,[Out,MarshalAs(UnmanagedType.LPArray,SizeParamIndex=0)] float[] values);
 [PreserveSig] int QueryHardwareSupport(out uint flags);
}
public static class OutputPeakProbe {
 public static float[] Read() {
  IPeakEnumerator enumerator=(IPeakEnumerator)(object)new PeakDeviceEnumerator();
  IPeakDevice device;Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0,1,out device));
  Guid iid=typeof(IPeakMeter).GUID;object instance;
  Marshal.ThrowExceptionForHR(device.Activate(ref iid,23,IntPtr.Zero,out instance));
  var meter=(IPeakMeter)instance;uint count;Marshal.ThrowExceptionForHR(meter.GetMeteringChannelCount(out count));
  var values=new float[count];Marshal.ThrowExceptionForHR(meter.GetChannelsPeakValues(count,values));
  Marshal.ReleaseComObject(instance);Marshal.ReleaseComObject(device);Marshal.ReleaseComObject(enumerator);return values;
 }
}
'@
$probeWatch = [Diagnostics.Stopwatch]::StartNew()
$probeBins = @{}
while ($probeWatch.Elapsed.TotalSeconds -lt $Seconds) {
  $probeSecond = [int][Math]::Floor($probeWatch.Elapsed.TotalSeconds)
  $probeLevels = [OutputPeakProbe]::Read()
  if (-not $probeBins.ContainsKey($probeSecond)) { $probeBins[$probeSecond] = New-Object double[] $probeLevels.Length }
  for ($probeChannel=0; $probeChannel -lt $probeLevels.Length; $probeChannel++) {
    $probeBins[$probeSecond][$probeChannel] = [Math]::Max($probeBins[$probeSecond][$probeChannel],$probeLevels[$probeChannel])
  }
  Start-Sleep -Milliseconds 25
}
$probeBins.GetEnumerator() | Sort-Object Name | ForEach-Object {
  [pscustomobject]@{Second=$_.Key;ChannelPeaks=$_.Value}
} | ConvertTo-Json -Depth 3
