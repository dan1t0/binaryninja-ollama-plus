from .plugin import *

# Cambiar el prefijo del menú para distinguirlo
MENU_PREFIX = r"Ollama+"

PluginCommand.register(f"{MENU_PREFIX}\Rename all functions", "Rename all functions based on (HLIL)", rename_all_functions_command)

PluginCommand.register_for_high_level_il_function(f"{MENU_PREFIX}\Rename target function", "Rename target function based on (HLIL)",
                            rename_function_HLIL_command)

PluginCommand.register_for_high_level_il_function(f"{MENU_PREFIX}\Rename all function variables", "Rename target function variables based on (HLIL)",
                            rename_function_variables_command)

PluginCommand.register_for_high_level_il_instruction(f"{MENU_PREFIX}\Rename target variable", "Rename target variable based on (HLIL)",
                            rename_variable_command)

PluginCommand.register(f"{MENU_PREFIX}\Settings\Set ollama model", "set the model you want to run", set_model_dialog)

PluginCommand.register(f"{MENU_PREFIX}\Settings\Set ollama server", "set the server where you want to access ollama", set_server_dialog)

PluginCommand.register_for_high_level_il_function(
    f"{MENU_PREFIX}\Explain function",
    "Get an explanation of what the function does",
    lambda bv, func: OllamaClient(bv).explain_function(func)
)

PluginCommand.register_for_high_level_il_function(
    f"{MENU_PREFIX}\Analyze vulnerabilities",
    "Analyze function for potential vulnerabilities",
    lambda bv, func: OllamaClient(bv).analyze_function_vulnerabilities(func)
)

