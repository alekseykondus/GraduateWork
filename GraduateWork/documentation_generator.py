import os
import ast
import time
import click
import openai
import ast_comments as astcom
from openai.error import RateLimitError


class DocumentationGenerator:
    def __init__(self, language, api_key):
        self.language = language
        openai.api_key = api_key
        self.ignored_dirs = ['.git',
                             '.idea',
                             '__pycache__',
                             'venv',
                             '.vscode',
                             'dist',
                             'build',
                             '*.pyc',
                             '*.pyo',
                             '*.pyd',
                             '*.pyz',
                             '*.pyw',
                             '*.egg-info',
                             '*.egg',
                             '*.dist-info']

    def get_ignored_dirs(self):
        return self.ignored_dirs

    def generate_docs(self, code):
        prompt = self._get_prompt(code)
        message = [{"role": "user", "content": prompt}]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            max_tokens=2048,
            temperature=1.2,
            messages=message
        )

        answer = response['choices'][0]['message']['content']
        return answer.strip()

    def _get_prompt(self, code):
        # if self.language == "Java":
        #    return "You task is to write Javadoc for a given code block. I need to document a function, class, module. Write me a docstring that describes what the function, class, module does, what parameters it accepts and returns, and what exceptions may occur during its execution. Also, please make sure that the documentation complies with the Javadoc standards. The code should not be modified, only the docstrings should be added. Once the docstring is added, please send me the updated code block with the new documentation.. For the following Python code:\n\n" + str(code) + "\n\nYou must return the result as code, DON'T DELETE a single line of code"
        if self.language == "Python":
            return "You task is to write docstrings for a given code block. I need to document a function, class, module. Write me a docstring that describes what the function, class, module does, what parameters it accepts and returns, and what exceptions may occur during its execution. Also, please make sure that the documentation complies with the PEP 257 standards. The code should not be modified, only the docstrings should be added. Once the docstring is added, please send me the updated code block with the new documentation.. For the following Python code:\n\n" + str(
                code) + "\n\nYou must return the result as code, DON'T DELETE a single line of code"

    def is_method(self, function_node, ast_tree):
        return isinstance(function_node.parent, ast.ClassDef)

    def generate_docs_for_block_and_change_node(self, tree, node, debug=False):
        try:
            code_with_docs = self.generate_docs(ast.unparse(node))
        except RateLimitError:
            print("Rate limit exceeded. Waiting for 20 seconds...")
            time.sleep(21)
            code_with_docs = self.generate_docs(ast.unparse(node))

        result = code_with_docs
        if debug:
            print(result)
            print(
                "----------------------------------------------------------------------------------------------------------------------------")

        old_node_index = tree.body.index(node)
        try:
            tree.body[old_node_index] = astcom.parse(result)
        except SyntaxError as e:
            print(f"Syntax error: {e}")
            print("Repeated demand")
            self.generate_docs_for_block_and_change_node(tree, node, debug)

    def generate_docs_for_code_from_file(self, file_path, debug=False):
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
            elif isinstance(node, ast.FunctionDef) and not self.is_method(node, tree):
                if debug:
                    code_block.append(node)
                self.generate_docs_for_block_and_change_node(tree, node, debug)

        new_source_code = astcom.unparse(tree)
        with open(file_path, 'w') as f:
            f.write(new_source_code)

    def is_ignored_directory(self, directory_name):
        return directory_name in self.ignored_dirs

    def generate_docs_for_code_from_dir(self, dir_path):
        for filename in os.listdir(dir_path):
            path = os.path.join(dir_path, filename)
            if os.path.isdir(path):
                directory_name = os.path.basename(path)
                if self.is_ignored_directory(directory_name):
                    continue
                self.generate_docs_for_code_from_dir(path)
            if self.language == "Python":
                if os.path.splitext(filename)[1] == ".py":
                    print(path)
                    self.generate_docs_for_code_from_file(str(path), debug=False)
            elif self.language == "Java":
                if os.path.splitext(filename)[1] == ".java":
                    print(path)
                    self.generate_docs_for_code_from_file(str(path), debug=False)

class DoxygenGenerator:
    def generate_Doxyfile(self, path, excluded_dirs):
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
        self.generate_Doxyfile(path, excluded_dirs)
        os.system('doxygen Doxyfile')

@click.command()
@click.option('--path', '-p', help='The path to the folder or file for documentation.')
@click.option('--doxygen', '-d', is_flag=True, help='Will launch Doxygen for the given path.')
def main(path, doxygen):
    if path:
        click.echo(f'I document the path: {path}')

        if os.path.isfile(path):
            doc_generator = DocumentationGenerator(language='Python', api_key="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")
            doc_generator.generate_docs_for_code_from_file(path, debug=False)
        elif os.path.isdir(path):
            doc_generator = DocumentationGenerator(language='Python', api_key="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")
            doc_generator.generate_docs_for_code_from_dir(path)
        else:
            click.echo('The path is not valid, please specify a valid path.')

        if doxygen:
            click.echo('Starting Doxygen...')
            doxygen_generator = DoxygenGenerator()
            doxygen_generator.generate_doxygen_documentation(path, doc_generator.get_ignored_dirs())
    else:
        click.echo('Please specify the path to the folder or file.')


if __name__ == "__main__":
    main()
