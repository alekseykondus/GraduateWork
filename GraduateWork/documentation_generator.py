
import os
import ast
import time
import click
import openai
import ast_comments as astcom
from openai.error import RateLimitError

class DocumentationGenerator:
    """This class is responsible for generating documentation for Python and Java code.
    Its methods can be used for individual code blocks as well as entire directories of code.

    Args:
    language (str): The programming language of the code to be documented ('Python' or 'Java').
    OpenAI API_key: The API key for authenticating OpenAI account.

    Attributes:
    language (str): The programming language of the code to be documented ('Python' or 'Java').
    ignored_dirs (list): A list of directory names to be ignored during documentation generation.

    Methods:
    get_ignored_dirs: Returns the list of directories to be ignored.
    generate_docs: Generates the documentation for a given code block.
        - code (str): The code block to be documented.
        return (str): The generated documentation.
    _get_prompt: Generate prompt message necessary for OpenAI chat completion API for generating docs
        - code (str): The code block we're generating a prompt for.
        return (str): The complete prompt message.
    is_method: Returns True if the function_node is a method within a class.
        - function_node: The function node in the AST.
        - ast_tree: The full AST of the code.
    generate_docs_for_block_and_change_node: Generates docstrings for a block of code and replaces the existing node with new node.
        - tree: The full AST of the code.
        - node: The code block node to generate documentation for.
        - debug (bool, optional): If True, gives verbose output during execution.
    generate_docs_for_code_from_file: Generates documentation for code in a file.
        - file_path (str): The path to the file containing the code to be documented.
        - debug (bool, optional): If True, gives verbose output during execution.
    is_ignored_directory: Returns True if the directory_name argument matches any directory names in the ignored_dirs attribute.
        - directory_name (str): The name of the directory in question.
    generate_docs_for_code_from_dir: Recursively generates documentation for code in all files in a given directory.
        - dir_path (str): The path to the top level dir in the directory structure containing the code to be documented.
    """

    def __init__(self, language, api_key):
        self.language = language
        openai.api_key = api_key
        self.ignored_dirs = ['.git', '.idea', '__pycache__', 'venv', '.vscode', 'dist', 'build', '*.pyc', '*.pyo', '*.pyd', '*.pyz', '*.pyw', '*.egg-info', '*.egg', '*.dist-info']

    def get_ignored_dirs(self):
        """Access the ignored_dirs attribute of the class.

        Returns:
        ignored_dirs (List[str]): A list of directory names to be ignored when scanning a directory for code.
        """
        return self.ignored_dirs

    def generate_docs(self, code):
        """Generates documentation for a block of code using the GPT-3 API from OpenAI.

        Args:
        code (str): The code block to be documented.

        Returns:
        answer (str): The generated documentation.
        """
        prompt = self._get_prompt(code)
        message = [{'role': 'user', 'content': prompt}]
        response = openai.ChatCompletion.create(model='gpt-3.5-turbo', max_tokens=2048, temperature=1.2, messages=message)
        answer = response['choices'][0]['message']['content']
        return answer.strip()

    def _get_prompt(self, code):
        """Generates prompt message and returns it with given code block for OpenAI API.

        Args:
        code (str): The code block to be documented

            Returns:
            (str): The prompt message with the given code.
            """
        if self.language == 'Python':
            return 'You task is to write docstrings for a given code block. I need to document a function, class, module. Write me a docstring that describes what the function, class, module does, what parameters it accepts and returns, and what exceptions may occur during its execution. Also, please make sure that the documentation complies with the PEP 257 standards. The code should not be modified, only the docstrings should be added. Once the docstring is added, please send me the updated code block with the new documentation.. For the following Python code:\n\n' + str(code) + "\n\nYou must return the result as code, DON'T DELETE a single line of code"

    def is_method(self, function_node, ast_tree):
        """Returns True if the function_node is a function node within a class node.

        Args:
        function_node: The function node in the AST.
        ast_tree: The full AST of the code.

        Returns:
        bool: True if the function_node is a method within a class.
        """
        return isinstance(function_node.parent, ast.ClassDef)

    def generate_docs_for_block_and_change_node(self, tree, node, debug=False):
        """Generates docstring for a block of code and replaces the existing node with new node.

        Args:
        tree: The full AST of the code.
        node: The code block node to generate documentation for.
        debug (bool, optional): If True, gives verbose output during execution.
        """
        try:
            code_with_docs = self.generate_docs(ast.unparse(node))
        except RateLimitError:
            print('Rate limit exceeded. Waiting for 20 seconds...')
            time.sleep(21)
            code_with_docs = self.generate_docs(ast.unparse(node))
        result = code_with_docs
        old_node_index = tree.body.index(node)
        try:
            tree.body[old_node_index] = astcom.parse(result)
        except SyntaxError as e:
            print(f'Syntax error: {e}')
            print('Repeated demand')
            self.generate_docs_for_block_and_change_node(tree, node, debug)

    def generate_docs_for_code_from_file(self, file_path, debug=False):
        """Loads code from a Python or Java file, generates documentation and adds it overwriting original file.

        Args:
        file_path (str): The path to the file containing the code.
        debug (bool, optional): If True, gives verbose output during execution.
        """
        with open(file_path, 'r') as file:
            source_code = file.read()
        tree = astcom.parse(source_code, type_comments=True)
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node
        if debug:
            code_block = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if debug:
                    code_block.append(node)
                self.generate_docs_for_block_and_change_node(tree, node, debug)
            elif isinstance(node, ast.FunctionDef) and (not self.is_method(node, tree)):
                if debug:
                    code_block.append(node)
                self.generate_docs_for_block_and_change_node(tree, node, debug)
        new_source_code = astcom.unparse(tree)
        with open(file_path, 'w') as f:
            f.write(new_source_code)

    def is_ignored_directory(self, directory_name):
        """Returns True if the directory_name argument matches a directory name in the ignored_dirs list.

        Args:
        directory_name (str): The name of the directory in question.

        Returns:
        bool: True if the directory is to be ignored, False otherwise.
        """
        return directory_name in self.ignored_dirs

    def generate_docs_for_code_from_dir(self, dir_path):
        """Recursively generates documentation for all code in all files underneath a given directory.

        Args:
        dir_path (str): The path to the top-level directory containing all code to be documented.
        """
        for filename in os.listdir(dir_path):
            path = os.path.join(dir_path, filename)
            if os.path.isdir(path):
                directory_name = os.path.basename(path)
                if self.is_ignored_directory(directory_name):
                    continue
                self.generate_docs_for_code_from_dir(path)
            if self.language == 'Python':
                if os.path.splitext(filename)[1] == '.py':
                    print(path)
                    self.generate_docs_for_code_from_file(str(path), debug=False)
            elif self.language == 'Java':
                if os.path.splitext(filename)[1] == '.java':
                    print(path)
                    self.generate_docs_for_code_from_file(str(path), debug=False)

class DoxygenGenerator:
    """
    Class that generates Doxygen documentation.

    Methods:
    1) generate_Doxyfile(path, excluded_dirs):
        - Generates a Doxyfile based on given path and excluded directories.
        - Parameters:
            - path (str): Path to file or directory for which documentation needs to be generated
            - excluded_dirs (list): List of directories to exclude from documentation generation
        - Returns: None
        - Raises: None

    2) generate_doxygen_documentation(path, excluded_dirs):
        - Generates Doxygen documentation for the given path using generate_Doxyfile method and
        using 'doxygen' command.
        - Parameters:
            - path (str): Path to file or directory for which documentation needs to be generated
            - excluded_dirs (list): List of directories to exclude from documentation generation
        - Returns: None
        - Raises: None
    """

    def generate_Doxyfile(self, path, excluded_dirs):
        """
        Method that generates a Doxyfile based on given path and excluded directories.

        Parameters:
        - path (str): Path to file or directory for which documentation needs to be generated
        - excluded_dirs (list): List of directories to exclude from documentation generation

        Returns: None

        Raises: None
        """
        with open('Doxyfile', 'w') as file:
            file.write('PROJECT_NAME = "Example"\n')
            file.write('INPUT = ' + str(path) + '\n')
            file.write('RECURSIVE = YES\n')
            file.write('GENERATE_HTML = YES\n')
            file.write('GENERATE_HTML = YES\n')
            file.write('EXCLUDE = ' + ' \\\n'.join(excluded_dirs))
            if not os.path.exists('/content/drive/MyDrive/docs/'):
                os.makedirs('/content/drive/MyDrive/docs/')
            if not os.path.exists('/content/drive/MyDrive/docs/' + os.path.basename(path)):
                os.makedirs('/content/drive/MyDrive/docs/' + os.path.basename(path))
            if os.path.isdir(path):
                file.write('HTML_OUTPUT = /content/drive/MyDrive/docs/' + os.path.basename(path) + '/html/' + '\n')
                file.write('LATEX_OUTPUT = /content/drive/MyDrive/docs/' + os.path.basename(path) + '/latex/' + '\n')
            elif os.path.isfile(path):
                if not os.path.exists(os.path.splitext(path)[0]):
                    os.makedirs(os.path.splitext(path)[0])
                file.write('HTML_OUTPUT = /content/drive/MyDrive/docs/' + os.path.splitext(path)[0] + '/html/' + '\n')
                file.write('LATEX_OUTPUT = /content/drive/MyDrive/docs/' + os.path.splitext(path)[0] + '/latex/' + '\n')
            file.write('EXTRACT_ALL = YES\n')
            file.write('echo "FILTER_PATTERNS = *.py=doxypypy"\n')

    def generate_doxygen_documentation(self, path, excluded_dirs):
        """
        Method that generates Doxygen documentation for the given path using generate_Doxyfile
        method and using 'doxygen' command.

        Parameters:
        - path (str): Path to file or directory for which documentation needs to be generated
        - excluded_dirs (list): List of directories to exclude from documentation generation

        Returns: None

        Raises: None
        """
        self.generate_Doxyfile(path, excluded_dirs)
        os.system('doxygen Doxyfile')


@click.command()
@click.option('--path', '-p', help='The path to the folder or file for documentation.')
@click.option('--doxygen', '-d', is_flag=True, help='Will launch Doxygen for the given path.')
def main(path, doxygen):
    """
    This function is the main entry point in the application which generates documentation for the given code either
    from a single file or a directory and, additionally, launches Doxygen for it if specified.

    Parameters:
    -----------
    path : str
        The file path or directory of the code for which documentation is to be generated.
    doxygen : bool
        A flag to launch Doxygen for the given directory or file.

    Returns:
    --------
    None

    Raises:
    -------
    None
    """
    if path:
        click.echo(f'I document the path: {path}')
        if os.path.isfile(path):
            doc_generator = DocumentationGenerator(language='Python',
                                                   api_key='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')
            doc_generator.generate_docs_for_code_from_file(path, debug=False)
        elif os.path.isdir(path):
            doc_generator = DocumentationGenerator(language='Python',
                                                   api_key='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')
            doc_generator.generate_docs_for_code_from_dir(path)
        else:
            click.echo('The path is not valid, please specify a valid path.')
        if doxygen:
            click.echo('Starting Doxygen...')
            doxygen_generator = DoxygenGenerator()
            doxygen_generator.generate_doxygen_documentation(path, doc_generator.get_ignored_dirs())
    else:
        click.echo('Please specify the path to the folder or file.')


if __name__ == '__main__':
    main()