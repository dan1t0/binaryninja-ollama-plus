from requests import Session
from binaryninja import log_info
from .rename_tasks import RenameAllFunctions, RenameVariable, RenameFunction, RenameFunctionVariables, ExplainFunction, AnalyzeVulnerabilities

class OllamaClient:
    """
    A singleton class to interact with the Ollama server for renaming functions and variables.
    """
    _instance = None

    def __new__(cls, bv):
        """
        Ensure that only one instance of the class is created.

        Args:
            bv (BinaryView): The current BinaryView instance.

        Returns:
            OllamaClient: The single instance of the OllamaClient class.
        """
        if cls._instance is None:
            cls._instance = super(OllamaClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, bv):
        """
        Initialize the OllamaClient instance.

        Args:
            bv (BinaryView): The current BinaryView instance.
        """
        if not self._initialized:
            self.bv = bv
            self.host = None
            self.port = None
            self.client = Session()
            self.model = None
            self._initialized = True

    def get_host(self):
        """
        Get the current host.

        Returns:
            str: The current host.
        """
        return self.host

    def get_port(self):
        """
        Get the current port.

        Returns:
            str: The current port.
        """
        return self.port

    def get_model(self):
        """
        Get the current model.

        Returns:
            str: The current model.
        """
        return self.model

    def set_host(self, host):
        """
        Set the host.

        Args:
            host (str): The host to be set.
        """
        self.host = host

    def set_port(self, port):
        """
        Set the port.

        Args:
            port (str): The port to be set.
        """
        self.port = port 

    def set_model(self, model):
        """
        Set the model.

        Args:
            model (str): The model to be set.
        """
        self.model = model
    
    def init_client(self):
        """
        Initialize the Ollama client.
        """
        if self.host is not None and self.port is not None:
            self.client = Session()

    def is_set(self):
        """
        Check if the host and port are set.

        Returns:
            bool: True if host and port are set, False otherwise.
        """
        if all(x is not None for x in (self.host, self.port)):
            return True
        return False

    def get_available_models(self):
        """
        Retrieve the list of available models from the Ollama server.

        Returns:
            list: A list of model names available on the Ollama server.

        Raises:
            RuntimeError: If the host or port is not set.
            Exception: For any errors encountered during the API call.
        """
        if not self.host or not self.port:
            raise RuntimeError("Host and port must be configured before fetching models.")

        try:
            response = self.client.get(f"http://{self.host}:{self.port}/v1/models")
            if response.status_code == 200:
                data = response.json()
                # Extraer los IDs de los modelos de la respuesta
                return [model['id'] for model in data.get('data', [])]
            else:
                raise Exception(f"Server returned status code {response.status_code}")
        except Exception as e:
            raise Exception("Failed to retrieve models from the Ollama server.") from e

    def get_variable_name(self, variable, hlil):
        """
        Get a suggested name for a variable.

        Args:
            variable (str): The current variable name.
            hlil (str): The HLIL decompiled code snippet.

        Returns:
            str: The suggested variable name.
        """
        prompt = (
                     f"In one word, what should the variable '{variable}' be named in the below Function? "
                     f"The name must meet the following criteria: all lowercase letters, usable in Python code"
        )
        prompt += f"Function:\n{hlil}\n\n"
        response = self.generate(
            model=self.model,
            prompt=prompt,
            stream=False
        ) 
        
        if response and 'response' in response:
            # Tomar la primera línea y limpiar espacios
            variable_name = response['response'].strip().split('\n')[0].strip()
            # Tomar solo la primera palabra y eliminar backticks
            variable_name = variable_name.split()[0].strip('`') if variable_name else None
            
            # Verificar que el nombre es válido (una sola palabra en minúsculas)
            if variable_name and variable_name.islower() and ' ' not in variable_name:
                return variable_name
        
        return None

    def get_function_name(self, hlil):
        """
        Get a suggested name for a function.

        Args:
            hlil (str): The HLIL decompiled code snippet.

        Returns:
            str: The suggested function name.
        """
        prompt = (
            f"Given the following HLIL decompiled code snippet, provide a Python-style function name that describes what the code is doing. "
            f"The name must meet the following criteria: all lowercase letters, usable in Python code, with underscores between words. "
            f"Only return the function name and no other explanation or text data included."
        )
        prompt += f"Function:\n{hlil}\n\n"
        response = self.generate(
            model=self.model,
            prompt=prompt,
            stream=False
        ) 
        
        # Procesar la respuesta para extraer solo el nombre de la función
        if response and 'response' in response:
            # Tomar la primera línea y limpiar espacios
            function_name = response['response'].strip().split('\n')[0].strip()
            # Eliminar cualquier texto adicional después del nombre de la función
            function_name = function_name.split()[0] if function_name else None
            
            # Verificar que el nombre cumple con los criterios
            if function_name and function_name.islower() and '_' in function_name:
                return function_name
        
        return None
    
    def generate(self, model, prompt, stream):
        """
        Generate a response from the Ollama server.

        Args:
            model (str): The model to be used.
            prompt (str): The prompt to be sent.
            stream (bool): Whether to stream the response.

        Returns:
            dict: The response from the server.
        """
        url = f"http://{self.host}:{self.port}/api/generate"
        data = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            # Parámetros de generación
            "temperature": 0.2,        # Menor temperatura para respuestas más deterministas
            "num_predict": 4096,       # Máximo número de tokens a generar
            "top_k": 40,              # Limita la selección a los 40 tokens más probables
            "top_p": 0.9,             # Nucleus sampling, reduce aleatoriedad manteniendo diversidad
            "repeat_penalty": 1.1,     # Penaliza la repetición de tokens
            "stop": ["\n\n", "```"],  # Detiene la generación en estos tokens
            "num_ctx": 4096           # Tamaño del contexto de entrada
        }
        response = self.client.post(url, json=data)
        if response.status_code == 200:
            return {"response": response.json()["response"]}
        else:
            raise Exception(f"Server returned status code {response.status_code}")

    def rename_function_variables(self, hlil):
        """
        Rename the variables of a function.

        Args:
            hlil (str): The HLIL decompiled code snippet.
        """
        rename_function_variables = RenameFunctionVariables(self, self.bv, hlil)
        rename_function_variables.start()

    def rename_target_variable(self, inst):
        """
        Rename a target variable.

        Args:
            inst (Instruction): The instruction containing the variable to be renamed.
        """
        rename_target_variable = RenameVariable(self, self.bv, inst)
        rename_target_variable.start()

    def rename_target_function(self, hlil):
        """
        Rename a target function.

        Args:
            hlil (str): The HLIL decompiled code snippet.
        """
        rename_target_function = RenameFunction(self, self.bv, hlil)
        rename_target_function.start()

    def rename_all_functions(self):
        """
        Rename all functions in the current BinaryView.
        """
        rename_all_functions = RenameAllFunctions(self, self.bv)
        rename_all_functions.start()

    def get_function_explanation(self, hlil):
        """
        Get an explanation of what the function or code block does.

        Args:
            hlil (str): The HLIL decompiled code snippet.

        Returns:
            str: The explanation of the function/code.
        """
        prompt = (
            f"Analyze the following decompiled code snippet and explain its functionality. "
            f"Focus on the main purpose, inputs, outputs, and key operations. "
            f"Provide a clear and concise technical explanation."
        )
        prompt += f"\nCode:\n{hlil}\n\n"
        response = self.generate(
            model=self.model,
            prompt=prompt,
            stream=False
        ) 
        
        if response and 'response' in response:
            explanation = response['response'].strip()
            if explanation:
                log_info("------------------")
                log_info("Function Explanation:")
                log_info(explanation)
                log_info("------------------")
                return explanation
        return None

    def analyze_vulnerabilities(self, hlil):
        """
        Analyze the code for potential security vulnerabilities.

        Args:
            hlil (str): The HLIL decompiled code snippet.

        Returns:
            str: The vulnerability analysis report.
        """
        prompt = (
            f"Analyze the following decompiled code for potential security vulnerabilities. "
            f"Focus on: buffer overflows, stack overflows, integer overflows, use-after-free, "
            f"format string vulnerabilities, and any other security-critical issues. "
            f"If vulnerabilities are found, explain why they are dangerous and how they could be exploited. "
            f"If no obvious vulnerabilities are found, explain why the code appears secure."
        )
        prompt += f"\nCode:\n{hlil}\n\n"
        response = self.generate(
            model=self.model,
            prompt=prompt,
            stream=False
        ) 
        
        if response and 'response' in response:
            analysis = response['response'].strip()
            if analysis:
                log_info("------------------")
                log_info("Vulnerability Analysis:")
                log_info(analysis)
                log_info("------------------")
                return analysis
        return None

    def explain_function(self, hlil):
        """
        Get an explanation of a function.

        Args:
            hlil (HighLevelILFunction): The HLIL representation of the function.
        """
        explain_function = ExplainFunction(self, self.bv, hlil)
        explain_function.start()

    def analyze_function_vulnerabilities(self, hlil):
        """
        Analyze a function for vulnerabilities.

        Args:
            hlil (HighLevelILFunction): The HLIL representation of the function.
        """
        analyze_vulnerabilities = AnalyzeVulnerabilities(self, self.bv, hlil)
        analyze_vulnerabilities.start()

