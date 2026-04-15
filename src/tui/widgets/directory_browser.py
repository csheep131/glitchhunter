"""Directory Browser Widget - TUI Verzeichnisauswahl."""

from pathlib import Path
from typing import Callable, Optional

from textual.widgets import Tree, Static, Button
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual.message import Message


class DirectoryBrowserWidget(Vertical):
    """Widget für Verzeichnisauswahl mit Tree-View."""

    DEFAULT_CSS = """
    DirectoryBrowserWidget {
        height: auto;
        max-height: 20;
        border: solid $primary;
        padding: 1;
    }
    DirectoryBrowserWidget Static {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    DirectoryBrowserWidget Tree {
        height: 1fr;
        border: solid $surface-darken-2;
        padding: 0 1;
    }
    DirectoryBrowserWidget Horizontal {
        height: auto;
        margin-top: 1;
    }
    DirectoryBrowserWidget Button {
        margin: 0 1;
    }
    """

    # Reactive state
    selected_path = reactive(Path.home())

    def __init__(
        self,
        start_path: Optional[Path] = None,
        on_select: Optional[Callable[[Path], None]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        # Dynamic home detection
        self.start_path = start_path or Path.home()
        if not start_path and (self.start_path / "projects").exists():
            self.start_path = self.start_path / "projects"
        
        self.on_select_callback = on_select
        self.dir_tree: Optional[Tree] = None

    def compose(self):
        """Compose the widget."""
        yield Static("📁 Verzeichnis auswählen:")

        # Create tree with root
        self.dir_tree = Tree(str(self.start_path), id="dir-tree")
        self.dir_tree.root.data = self.start_path
        self.dir_tree.root.expand()
        yield self.dir_tree

        with Horizontal():
            yield Button("⬆️ Hoch", id="btn-up")
            yield Button("📂 Öffnen", id="btn-open", variant="primary")
            yield Button("✅ Auswählen", id="btn-select", variant="success")

        # Initial population
        self._populate_tree(self.dir_tree.root)

    def _populate_tree(self, node):
        """Populate tree node with directory contents."""
        path = node.data
        if not path or not path.is_dir():
            return

        try:
            # Get subdirectories
            subdirs = [
                p for p in path.iterdir()
                if p.is_dir() and not p.name.startswith('.')
            ]
            subdirs.sort(key=lambda p: p.name.lower())

            for subdir in subdirs:
                child = node.add(subdir.name, data=subdir)
                # Add dummy child to show expand arrow
                if any(
                    p.is_dir() and not p.name.startswith('.')
                    for p in subdir.iterdir()
                ):
                    child.add("...", data=None)

        except PermissionError:
            node.add("[Permission Denied]", data=None)
        except Exception:
            pass

    def on_tree_node_expanded(self, event: Tree.NodeExpanded):
        """Handle node expansion."""
        node = event.node
        if node.data and node.data.is_dir():
            # Remove dummy children if any
            if len(node.children) == 1 and node.children[0].data is None:
                node.children[0].remove()
                self._populate_tree(node)

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Handle node selection."""
        node = event.node
        if node.data and node.data.is_dir():
            self.selected_path = node.data

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-up":
            self._go_up()
        elif event.button.id == "btn-open":
            self._open_selected()
        elif event.button.id == "btn-select":
            self._select_current()

    def _go_up(self):
        """Go to parent directory."""
        parent = self.selected_path.parent
        if parent != self.selected_path:
            self.selected_path = parent
            self._refresh_tree()

    def _open_selected(self):
        """Open/expand selected directory."""
        if self.dir_tree and self.selected_path.is_dir():
            # Find and expand the node
            for child in self.dir_tree.root.children:
                if child.data == self.selected_path:
                    child.expand()
                    self._populate_tree(child)
                    break

    def _select_current(self):
        """Confirm selection of current path."""
        if self.on_select_callback:
            self.on_select_callback(self.selected_path)
        self.post_message(self.DirectorySelected(self.selected_path))

    def _refresh_tree(self):
        """Refresh tree from current path."""
        if not self.dir_tree:
            return
            
        self.dir_tree.root.remove_children()
        self.dir_tree.root.label = str(self.selected_path)
        self.dir_tree.root.data = self.selected_path
        self._populate_tree(self.dir_tree.root)

    def get_selected_path(self) -> Path:
        """Get currently selected path."""
        return self.selected_path

    class DirectorySelected(Message):
        """Message sent when directory is selected."""

        def __init__(self, path: Path):
            super().__init__()
            self.path = path


class ProjectSelectorWidget(Vertical):
    """Widget für Projekt-Auswahl mit Favoriten und History."""

    DEFAULT_CSS = """
    ProjectSelectorWidget {
        height: auto;
        border: solid $primary-lighten-1;
        padding: 1;
    }
    ProjectSelectorWidget Static {
        text-style: bold;
        color: $primary-lighten-1;
        margin-bottom: 1;
    }
    """

    # Favoriten-Liste (dynamisch)
    FAVORITES = [
        Path.home() / "projects",
        Path.home(),
        Path.home() / "projects/glitchhunter",
    ]

    def __init__(self, on_select: Optional[Callable[[Path], None]] = None, **kwargs):
        super().__init__(**kwargs)
        self.on_select = on_select

    def compose(self):
        """Compose the widget."""
        yield Static("⭐ Schnellzugriff:")

        for fav in self.FAVORITES:
            if fav.exists():
                btn = Button(
                    f"📂 {fav.name}",
                    id=f"fav-{fav.name}",
                    variant="primary" if fav == Path("/home/schaf/projects") else "default"
                )
                btn.data = fav
                yield btn

    def on_button_pressed(self, event: Button.Pressed):
        """Handle favorite selection."""
        if hasattr(event.button, 'data') and event.button.data:
            if self.on_select:
                self.on_select(event.button.data)
            self.post_message(DirectoryBrowserWidget.DirectorySelected(event.button.data))
