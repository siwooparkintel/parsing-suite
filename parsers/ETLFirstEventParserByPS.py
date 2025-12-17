import subprocess
import json
from typing import Dict, Optional

class ETLHighPrecisionTimeExtractor:
    """Extract high-precision timestamps from ETL files using PowerShell Get-WinEvent"""
    
    def __init__(self):
        self._validate_powershell()
    
    def _validate_powershell(self):
        """Check if PowerShell is available"""
        try:
            subprocess.run(['powershell', '-Command', 'Get-Host'], 
                         capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            raise EnvironmentError("PowerShell not available")
    
    def get_first_event_times(self, etl_file: str) -> Optional[Dict]:
        """
        Extract first event with high-precision timestamps
        
        Args:
            etl_file: Path to ETL file
            
        Returns:
            Dictionary with various timestamp formats
        """
        ps_script = f'''
        try {{
            $event = Get-WinEvent -Path "{etl_file}" -MaxEvents 1 -Oldest -ErrorAction Stop
            
            if ($event) {{
                $timeCreated = $event.TimeCreated
                $epochOffset = [DateTimeOffset]$timeCreated
                
                $result = @{{
                    'success' = $true
                    'datetime_original' = $timeCreated.ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
                    'filetime' = $timeCreated.ToFileTime()
                    'epoch_milliseconds' = $epochOffset.ToUnixTimeMilliseconds()
                    'event_id' = $event.Id
                }}
                
                $result | ConvertTo-Json -Compress
            }} else {{
                '{{"success": false, "error": "No events found"}}'
            }}
        }} catch {{
            '{{"success": false, "error": "' + $_.Exception.Message + '"}}'
        }}
        '''
        
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                if data.get('success'):
                    return {
                        'datetime_original': data['datetime_original'],
                        'filetime': int(data['filetime']),
                        'epoch_milliseconds': int(data['epoch_milliseconds']),
                        'event_id': data['event_id'],
                    }
                else:
                    raise RuntimeError(data.get('error', 'Unknown error'))
            else:
                raise RuntimeError(f"PowerShell error: {result.stderr}")
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Failed to extract timestamp: {str(e)}")
    
    def get_filetime_only(self, etl_file: str) -> Optional[int]:
        """Get only FILETIME from first event (fastest method)"""
        ps_script = f'''
        try {{
            $event = Get-WinEvent -Path "{etl_file}" -MaxEvents 1 -Oldest -ErrorAction Stop
            if ($event) {{
                $event.TimeCreated.ToFileTime()
            }}
        }} catch {{
            Write-Error $_.Exception.Message
        }}
        '''
        
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
            return None
            
        except (subprocess.TimeoutExpired, ValueError):
            return None

    def get_quick_first_event(self, etl_file: str) -> Optional[int]:
        """Get only FILETIME from first event (fastest method)"""
        ps_script = f'''
([DateTimeOffset](Get-WinEvent -Path "{etl_file}" -MaxEvents 1 -Oldest).TimeCreated).ToUnixTimeMilliseconds() 
        '''
        
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
            return None
            
        except (subprocess.TimeoutExpired, ValueError):
            return None
