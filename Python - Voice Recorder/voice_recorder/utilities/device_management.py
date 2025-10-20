"""Audio device management utilities.

Provides centralized audio device selection, validation, and status management.
Currently uses sounddevice library for device enumeration.

NO DUPLICATION of existing utilities:
- config_manager.py handles configuration (not runtime device state)
- This module complements config_manager by managing runtime device state
"""

from typing import List, Optional, Union

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

from voice_recorder.utilities.base import BaseManager
from voice_recorder.core.logging_config import get_logger

logger = get_logger(__name__)


class AudioDeviceManager(BaseManager):
    """Manage audio device selection and validation.
    
    Provides methods for selecting devices, validating selections,
    and querying available devices.
    
    Example:
        manager = AudioDeviceManager()
        devices = manager.get_available_devices()
        manager.set_selected_device(devices[0])
        selected = manager.get_selected_device()
    """
    
    def __init__(self):
        """Initialize the audio device manager."""
        super().__init__(manager_name="AudioDeviceManager")
        self._selected_device: Optional[Union[int, str]] = None
    
    def get_available_devices(self) -> List[dict]:
        """Get list of available audio devices.
        
        Returns:
            List of device dictionaries with device info
        """
        if not SOUNDDEVICE_AVAILABLE:
            logger.warning("sounddevice not available, returning empty device list")
            return []
        
        try:
            devices = sd.query_devices()
            if isinstance(devices, dict):
                return [devices]
            return list(devices)
        except Exception as e:
            logger.error(f"Failed to query audio devices: {e}")
            return []
    
    def set_selected_device(self, device: Optional[Union[int, str]]) -> bool:
        """Set the selected audio device.
        
        Args:
            device: Device index (int), device name (str), or None for default
        
        Returns:
            True if device is valid, False otherwise
        """
        if device is None:
            self._selected_device = None
            self.emit_status("Device: Default")
            return True
        
        if self.validate_device(device):
            self._selected_device = device
            device_str = str(device) if isinstance(device, int) else device
            self.emit_status(f"Device: {device_str}")
            logger.info(f"Selected audio device: {device}")
            return True
        
        logger.warning(f"Invalid device selection: {device}")
        return False
    
    def get_selected_device(self) -> Optional[Union[int, str]]:
        """Get the currently selected device.
        
        Returns:
            Device index/name or None for default
        """
        return self._selected_device
    
    def validate_device(self, device: Optional[Union[int, str]]) -> bool:
        """Validate that a device is available.
        
        Args:
            device: Device to validate
        
        Returns:
            True if device is valid or None (default), False if invalid
        """
        if device is None:
            return True
        
        if not SOUNDDEVICE_AVAILABLE:
            logger.warning("sounddevice not available, cannot validate device")
            return False
        
        try:
            available = self.get_available_devices()
            
            if isinstance(device, int):
                # Check if device index is valid
                return 0 <= device < len(available)
            
            if isinstance(device, str):
                # Check if device name exists
                device_names = [d.get("name", "") for d in available]
                return device in device_names
            
            return False
        
        except Exception as e:
            logger.error(f"Error validating device: {e}")
            return False
    
    def get_device_info(self, device: Optional[Union[int, str]]) -> Optional[dict]:
        """Get information about a specific device.
        
        Args:
            device: Device index or name
        
        Returns:
            Device info dictionary or None if not found
        """
        if device is None:
            try:
                if SOUNDDEVICE_AVAILABLE:
                    return sd.query_devices(kind='input')
            except Exception:
                pass
            return None
        
        if not self.validate_device(device):
            return None
        
        try:
            if SOUNDDEVICE_AVAILABLE:
                return sd.query_devices(device)
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
        
        return None
