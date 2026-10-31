import tree_sitter_python
from tree_sitter import Language, Parser

path = "test-repos/RAG-Anything/raganything/raganything.py"
source = open(path, "rb").read()

parser = Parser(Language(tree_sitter_python.language()))
root = parser.parse(source).root_node

leftover = []

for node in root.children:
    if node.type == "decorated_definition":
        node = node.child_by_field_name("definition")
    if node.type in ("function_definition", "class_definition"):
        name = node.child_by_field_name("name").text.decode()
        start = node.start_point[0] + 1
        end = node.end_point[0] + 1
        print(node.type, name, start, end)
    else:
        leftover.append(node)

if leftover:
    overview = b"\n".join(n.text for n in leftover).decode()
    print("file_overview", leftover[0].start_point[0] + 1,
leftover[-1].end_point[0] + 1)
    print(overview)
