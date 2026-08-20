from utils.config_manager import ConfigManager
cm = ConfigManager()
print(cm.get("enable_mirror", "Default Value if not exist"))
