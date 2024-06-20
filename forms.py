import uuid
from typing import Callable, Dict, List, Tuple, Union

import frontmatter
from pydantic import BaseModel, ConfigDict

HTML_TYPE = {"text", "number", "email", "submit", "textarea"}
CONTROL_TYPES = {"submit"}

RENDER_FUNCTIONS = {
    "text": lambda x: f'<input type="text" id="{x.id}" name="{x.name}" value="{x.value}" placeholder="{x.placeholder}">',
    "number": lambda x: f'<input type="number" id="{x.id}" name="{x.name}" value="{x.value}" placeholder="{x.placeholder}">',
    "email": lambda x: f'<input type="email" id="{x.id}" name="{x.name}" value="{x.value}" placeholder="{x.placeholder}">',
    "submit": lambda x: f'<button id="{x.id}" name="{x.name}">{x.value}</button>',
    "textarea": lambda x: f'<textarea id="{x.id}" name="{x.name}" placeholder="{x.placeholder}">{x.value}</textarea>',
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{form_name}</title>
    <link rel="stylesheet" href="styles.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap" rel="stylesheet">
</head>
<body>
    {content}
</body>
</html>
"""

def slugify(value: str) -> str:
    return value.replace(" ", "-").lower()


class FormItem(BaseModel):
    """
    A field in a form.
    """

    name: str
    value: str = ""
    placeholder: str = ""
    html_type: str = "text"
    id: str = str(uuid.uuid4())
    hooks: List[str] = []

    def _serialize_as_html(self) -> str:
        return "<label for='{id}'>{name}</label>{control}".format(
            id=self.id, name=self.name, control=RENDER_FUNCTIONS[self.html_type](self)
        )

    def _run_hooks(self):
        for hook in self.hooks:
            self.value = globals()[hook](self.value)


class Group(BaseModel):
    """
    A form group. Used to group related fields together.

    Form groups may be useful for rendering forms in separate areas in a user
    interface.
    """

    name: str
    items: List[FormItem]


class Form(BaseModel):
    """
    A form that can be rendered as HTML and saved to a file.
    """

    name: str
    groups: List[Group]
    front_matter: str = frontmatter.loads("")
    id: str = str(uuid.uuid4())

    @classmethod
    def load_from_specification(cls, specification: Dict):
        """
        Load a form from a specification.
        """
        return cls(**specification)

    def _serialize_as_html(self) -> str:
        html = f"<h1>{self.name}</h1><form action='/{self.id}' method='POST'>"
        for group in self.groups:
            html += f"<div class='group' id='{group.name}'>"
            for item in group.items:
                html += item._serialize_as_html()
            html += "</div>"

        html += "</form>"

        return html

    def save_to_file(self, path: str) -> None:
        """
        Save the form to a file as HTML.
        """
        with open(path, "w") as file:
            file.write(HTML_TEMPLATE.format(form_name=self.name, content=self._serialize_as_html()))

    def _serialize_as_front_matter(self) -> str:
        front_matter = self.front_matter
        front_matter["form_name"] = self.name
        for group in self.groups:
            for item in group.items:
                if item.html_type in CONTROL_TYPES:
                    continue

                item._run_hooks()

                front_matter[item.name.lower()] = item.value

        return front_matter.metadata


spec = {
    "name": "Publish a Blog Post",
    "groups": [
        {
            "name": "Post Details",
            "items": [
                {"name": "Title", "value": "Coffee", "html_type": "text"},
                {
                    "name": "Body",
                    "value": "This is a test!",
                    "html_type": "textarea",
                },
            ],
        },
        {
            "name": "Meta Information",
            "items": [
                {
                    "name": "Slug",
                    "value": "POST-EXAMPLE",
                    "html_type": "text",
                    "hooks": ["slugify"],
                },
            ],
        },
        {
            "name": "Publish",
            "items": [
                {"name": "Publish", "value": "Publish", "html_type": "submit"},
            ],
        }
    ],
}

forms = [Form.load_from_specification(spec)]

forms_as_dict = {form.id: form for form in forms}

for id, form in forms_as_dict.items():
    print(form._serialize_as_html(), "\n", id)

form.save_to_file("form.html")