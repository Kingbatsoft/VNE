"""
VNEditor - A text editor system for the Visual Novel Engine
Provides tools for writing, editing, and managing visual novel scripts
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import json
import os
import re
import shutil
import time
import difflib
from typing import Dict, List, Tuple, Optional, Any

class VNEditor:
    """Main editor class for the visual novel engine"""
    
    def __init__(self, title="Visual Novel Script Editor"):
        """Initialize the editor window and components"""
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self._confirm_exit)
        
        # Set app icon
        # self.root.iconbitmap("resources/icon.ico")  # Uncomment and add your icon
        
        # Editor state
        self.current_file = None
        self.text_modified = False
        self.auto_save_timer = None
        self.auto_save_interval = 5 * 60 * 1000  # 5 minutes in milliseconds
        
        # Version control
        self.version_history = []
        self.versions_dir = "versions"
        os.makedirs(self.versions_dir, exist_ok=True)
        
        # Project settings
        self.project_dir = None
        self.project_config = {
            'name': 'New Project',
            'author': 'Unknown',
            'version': '0.1',
            'description': 'A visual novel project',
            'resources': {
                'characters': {},
                'backgrounds': {},
                'music': {},
                'sound': {}
            }
        }
        
        # Character database
        self.characters = {}
        
        # Setup UI components
        self._setup_ui()
        
        # Start autosave
        self._start_auto_save()
    
    def _setup_ui(self):
        """Set up the editor user interface"""
        # Create menu bar
        self._setup_menu()
        
        # Create toolbar
        self._setup_toolbar()
        
        # Main content - use a PanedWindow for resizable sections
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - script editor
        self.editor_frame = ttk.Frame(self.main_paned)
        
        # Add a notebook for multiple script files
        self.editor_notebook = ttk.Notebook(self.editor_frame)
        self.editor_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create the first editor tab
        self._create_editor_tab("main.vn", "# Main Script\n\n")
        
        # Right panel - multi-tabbed interface
        self.right_panel = ttk.Frame(self.main_paned)
        self.right_notebook = ttk.Notebook(self.right_panel)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Preview tab
        self.preview_frame = ttk.Frame(self.right_notebook)
        self.preview_text = scrolledtext.ScrolledText(self.preview_frame, wrap=tk.WORD, font=("Arial", 11))
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        self.preview_text.config(state=tk.DISABLED)
        self.right_notebook.add(self.preview_frame, text="Preview")
        
        # Characters tab
        self.characters_frame = ttk.Frame(self.right_notebook)
        self._setup_characters_tab()
        self.right_notebook.add(self.characters_frame, text="Characters")
        
        # Scenes tab
        self.scenes_frame = ttk.Frame(self.right_notebook)
        self._setup_scenes_tab()
        self.right_notebook.add(self.scenes_frame, text="Scenes")
        
        # Resources tab
        self.resources_frame = ttk.Frame(self.right_notebook)
        self._setup_resources_tab()
        self.right_notebook.add(self.resources_frame, text="Resources")
        
        # Structure tab
        self.structure_frame = ttk.Frame(self.right_notebook)
        self._setup_structure_tab()
        self.right_notebook.add(self.structure_frame, text="Structure")
        
        # Add frames to main paned window
        self.main_paned.add(self.editor_frame, weight=3)
        self.main_paned.add(self.right_panel, weight=2)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Setup search dialog variables
        self.search_dialog = None
        self.search_var = tk.StringVar()
        self.replace_var = tk.StringVar()
    
    def _setup_menu(self):
        """Set up the menu bar"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project", command=self._new_project)
        file_menu.add_command(label="Open Project", command=self._open_project)
        file_menu.add_command(label="Save Project", command=self._save_project)
        file_menu.add_separator()
        file_menu.add_command(label="New File", command=self._new_file)
        file_menu.add_command(label="Open File", command=self._open_file)
        file_menu.add_command(label="Save", command=self._save_file)
        file_menu.add_command(label="Save As", command=self._save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Project Settings", command=self._project_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._confirm_exit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self._redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=self._cut, accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=self._copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=self._paste, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Find", command=self._show_search_dialog, accelerator="Ctrl+F")
        edit_menu.add_command(label="Replace", command=self._show_replace_dialog, accelerator="Ctrl+H")
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # Insert menu
        insert_menu = tk.Menu(menubar, tearoff=0)
        insert_menu.add_command(label="Character Dialogue", command=self._insert_character_dialogue)
        insert_menu.add_command(label="Character Expression", command=self._insert_character_expression)
        insert_menu.add_command(label="Choice", command=self._insert_choice)
        insert_menu.add_command(label="Scene", command=self._insert_scene)
        insert_menu.add_command(label="Background Music", command=self._insert_bgm)
        insert_menu.add_command(label="Sound Effect", command=self._insert_sound)
        menubar.add_cascade(label="Insert", menu=insert_menu)
        
        # Script menu
        script_menu = tk.Menu(menubar, tearoff=0)
        script_menu.add_command(label="Validate Script", command=self._validate_script)
        script_menu.add_command(label="Generate Preview", command=self._generate_preview)
        script_menu.add_separator()
        script_menu.add_command(label="Compile Script", command=self._compile_script)
        script_menu.add_command(label="Export Script", command=self._export_script)
        menubar.add_cascade(label="Script", menu=script_menu)
        
        # Version menu
        version_menu = tk.Menu(menubar, tearoff=0)
        version_menu.add_command(label="Save Version", command=self._save_version)
        version_menu.add_command(label="Load Version", command=self._load_version)
        version_menu.add_command(label="Compare Versions", command=self._compare_versions)
        menubar.add_cascade(label="Version", menu=version_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Character Manager", command=self._show_character_manager)
        tools_menu.add_command(label="Scene Manager", command=self._show_scene_manager)
        tools_menu.add_command(label="Resource Manager", command=self._show_resource_manager)
        tools_menu.add_separator()
        tools_menu.add_command(label="Script Statistics", command=self._show_statistics)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self._show_documentation)
        help_menu.add_command(label="Script Syntax", command=self._show_syntax_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def _setup_toolbar(self):
        """Set up the toolbar with common actions"""
        toolbar_frame = ttk.Frame(self.root)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        
        # File operations
        ttk.Button(toolbar_frame, text="New", command=self._new_file).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Open", command=self._open_file).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Save", command=self._save_file).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, pady=2, fill=tk.Y)
        
        # Edit operations
        ttk.Button(toolbar_frame, text="Undo", command=self._undo).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Redo", command=self._redo).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, pady=2, fill=tk.Y)
        
        # Insert operations
        ttk.Button(toolbar_frame, text="Character", command=self._insert_character_dialogue).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Choice", command=self._insert_choice).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Scene", command=self._insert_scene).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, pady=2, fill=tk.Y)
        
        # Script operations
        ttk.Button(toolbar_frame, text="Validate", command=self._validate_script).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Preview", command=self._generate_preview).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, pady=2, fill=tk.Y)
        
        # Format operations
        ttk.Button(toolbar_frame, text="Bold", command=lambda: self._format_text("**", "**")).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Italic", command=lambda: self._format_text("*", "*")).pack(side=tk.LEFT, padx=2, pady=2)
        
        # Add a button for quick format help
        ttk.Button(toolbar_frame, text="?", command=self._show_syntax_help, width=3).pack(side=tk.RIGHT, padx=2, pady=2)
    
    def _setup_characters_tab(self):
        """Set up the characters tab in the right panel"""
        # Add a frame for controls
        controls_frame = ttk.Frame(self.characters_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Add Character", command=self._add_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Edit Character", command=self._edit_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Remove Character", command=self._remove_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_characters).pack(side=tk.RIGHT, padx=5)
        
        # Add a treeview for displaying characters
        self.characters_tree = ttk.Treeview(self.characters_frame, columns=("expressions",))
        self.characters_tree.heading("#0", text="Character")
        self.characters_tree.heading("expressions", text="Expressions")
        self.characters_tree.column("#0", width=150)
        self.characters_tree.column("expressions", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.characters_frame, orient="vertical", command=self.characters_tree.yview)
        self.characters_tree.configure(yscrollcommand=scrollbar.set)
        
        self.characters_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to insert character
        self.characters_tree.bind("<Double-1>", self._insert_selected_character)
    
    def _setup_scenes_tab(self):
        """Set up the scenes tab in the right panel"""
        # Add a frame for controls
        controls_frame = ttk.Frame(self.scenes_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Add Scene", command=self._add_scene).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Edit Scene", command=self._edit_scene).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Remove Scene", command=self._remove_scene).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_scenes).pack(side=tk.RIGHT, padx=5)
        
        # Add a treeview for displaying scenes
        self.scenes_tree = ttk.Treeview(self.scenes_frame, columns=("file",))
        self.scenes_tree.heading("#0", text="Scene")
        self.scenes_tree.heading("file", text="File")
        self.scenes_tree.column("#0", width=150)
        self.scenes_tree.column("file", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.scenes_frame, orient="vertical", command=self.scenes_tree.yview)
        self.scenes_tree.configure(yscrollcommand=scrollbar.set)
        
        self.scenes_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to insert scene
        self.scenes_tree.bind("<Double-1>", self._insert_selected_scene)
    
    def _setup_resources_tab(self):
        """Set up the resources tab in the right panel"""
        # Add a frame for controls
        controls_frame = ttk.Frame(self.resources_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Add Resource", command=self._add_resource).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Import Resources", command=self._import_resources).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_resources).pack(side=tk.RIGHT, padx=5)
        
        # Add a treeview for displaying resources
        self.resources_tree = ttk.Treeview(self.resources_frame)
        self.resources_tree.heading("#0", text="Resources")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.resources_frame, orient="vertical", command=self.resources_tree.yview)
        self.resources_tree.configure(yscrollcommand=scrollbar.set)
        
        self.resources_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add initial resource categories
        categories = ["Backgrounds", "Characters", "Music", "Sound Effects"]
        for category in categories:
            self.resources_tree.insert("", "end", text=category, open=True)
        
        # Double-click to insert resource
        self.resources_tree.bind("<Double-1>", self._insert_selected_resource)
    
    def _setup_structure_tab(self):
        """Set up the structure tab in the right panel"""
        # Add a frame for controls
        controls_frame = ttk.Frame(self.structure_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Analyze Script", command=self._analyze_script_structure).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Navigate to Scene", command=self._navigate_to_scene).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Check Flow", command=self._check_script_flow).pack(side=tk.LEFT, padx=5)
        
        # Add a treeview for displaying script structure
        self.structure_tree = ttk.Treeview(self.structure_frame)
        self.structure_tree.heading("#0", text="Script Structure")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.structure_frame, orient="vertical", command=self.structure_tree.yview)
        self.structure_tree.configure(yscrollcommand=scrollbar.set)
        
        self.structure_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to navigate to structure element
        self.structure_tree.bind("<Double-1>", self._navigate_to_element)
    
    def _create_editor_tab(self, tab_name, initial_content=""):
        """Create a new editor tab with the specified name and content"""
        # Create a frame for the tab
        tab_frame = ttk.Frame(self.editor_notebook)
        
        # Create a text editor with syntax highlighting and line numbers
        text_frame = ttk.Frame(tab_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Line numbers
        line_numbers = tk.Text(text_frame, width=4, padx=3, takefocus=0, border=0,
                               background='#f0f0f0', state='disabled', wrap='none')
        line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main text editor
        text_editor = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, undo=True,
                                               font=("Consolas", 11), bg="#ffffff")
        text_editor.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Insert initial content
        if initial_content:
            text_editor.insert("1.0", initial_content)
        
        # Set up key bindings for the editor
        text_editor.bind("<KeyRelease>", lambda e, editor=text_editor: self._on_text_changed(editor))
        text_editor.bind("<Control-f>", lambda e: self._show_search_dialog())
        text_editor.bind("<Control-h>", lambda e: self._show_replace_dialog())
        text_editor.bind("<Control-s>", lambda e: self._save_file())
        
        # Set up line number updating
        text_editor.bind("<KeyRelease>", lambda e, editor=text_editor, numbers=line_numbers: 
                        self._update_line_numbers(editor, numbers))
        text_editor.bind("<MouseWheel>", lambda e, editor=text_editor, numbers=line_numbers: 
                        self._update_line_numbers(editor, numbers))
        
        # Initial line numbers
        self._update_line_numbers(text_editor, line_numbers)
        
        # Set up syntax highlighting
        self._setup_syntax_highlighting(text_editor)
        
        # Add the tab
        self.editor_notebook.add(tab_frame, text=tab_name)
        
        # Store reference to editor for this tab
        tab_frame.text_editor = text_editor
        tab_frame.line_numbers = line_numbers
        tab_frame.file_path = None
        
        # Switch to the new tab
        self.editor_notebook.select(len(self.editor_notebook.tabs()) - 1)
        
        # Return the created text editor widget
        return text_editor
    
    def _update_line_numbers(self, editor, line_numbers):
        """Update line numbers in the editor"""
        line_numbers.config(state='normal')
        line_numbers.delete('1.0', tk.END)
        
        # Get number of lines
        num_lines = editor.get('1.0', tk.END).count('\n')
        
        # Add line numbers
        line_num_content = '\n'.join(str(i) for i in range(1, num_lines + 1))
        line_numbers.insert('1.0', line_num_content)
        
        line_numbers.config(state='disabled')
    
    def _setup_syntax_highlighting(self, text_editor):
        """Set up syntax highlighting for the editor"""
        # Define tags for different elements
        text_editor.tag_configure("scene_tag", foreground="#0000FF")  # Blue
        text_editor.tag_configure("character_tag", foreground="#FF0000")  # Red
        text_editor.tag_configure("expression_tag", foreground="#FF8C00")  # Dark Orange
        text_editor.tag_configure("choice_tag", foreground="#008080")  # Teal
        text_editor.tag_configure("bgm_tag", foreground="#800080")  # Purple
        text_editor.tag_configure("sound_tag", foreground="#800080")  # Purple
        text_editor.tag_configure("comment_tag", foreground="#008000")  # Green
        text_editor.tag_configure("bold_tag", font=("Consolas", 11, "bold"))
        text_editor.tag_configure("italic_tag", font=("Consolas", 11, "italic"))
        
        # Bind events for syntax highlighting
        text_editor.bind("<KeyRelease>", lambda e, editor=text_editor: self._highlight_syntax(editor))
    
    def _highlight_syntax(self, text_editor):
        """Apply syntax highlighting to the editor content"""
        # Remove existing tags
        for tag in ["scene_tag", "character_tag", "expression_tag", "choice_tag", 
                   "bgm_tag", "sound_tag", "comment_tag", "bold_tag", "italic_tag"]:
            text_editor.tag_remove(tag, "1.0", tk.END)
        
        # Get all text
        content = text_editor.get("1.0", tk.END)
        
        # Define highlighting patterns
        patterns = [
            (r"@scene:.*", "scene_tag"),
            (r"@character:.*", "character_tag"),
            (r"@.*?:", "expression_tag"),
            (r"-> .*", "choice_tag"),
            (r"@bgm:.*", "bgm_tag"),
            (r"@sound:.*", "sound_tag"),
            (r"#.*", "comment_tag"),
            (r"\*\*.*?\*\*", "bold_tag"),
            (r"\*[^*].*?[^*]\*", "italic_tag")
        ]
        
        # Apply highlighting
        for pattern, tag in patterns:
            self._apply_highlight(text_editor, pattern, tag)
    
    def _apply_highlight(self, text_editor, pattern, tag):
        """Apply a highlight pattern to the editor"""
        # Get all text
        content = text_editor.get("1.0", tk.END)
        
        # Find all matches
        for match in re.finditer(pattern, content, re.MULTILINE):
            start_index = "1.0 + %dc" % match.start()
            end_index = "1.0 + %dc" % match.end()
            text_editor.tag_add(tag, start_index, end_index)
    
    def _get_current_editor(self):
        """Get the text editor widget for the current tab"""
        try:
            current_tab = self.editor_notebook.select()
            tab_index = self.editor_notebook.index(current_tab)
            tab_frame = self.editor_notebook.winfo_children()[tab_index]
            return tab_frame.text_editor
        except Exception as e:
            print(f"Error getting current editor: {e}")
            return None
    
    def _on_text_changed(self, editor):
        """Handle text changes in the editor"""
        # Update modified flag
        if not self.text_modified:
            self.text_modified = True
            current_tab = self.editor_notebook.select()
            tab_text = self.editor_notebook.tab(current_tab, "text")
            if not tab_text.endswith("*"):
                self.editor_notebook.tab(current_tab, text=tab_text + "*")
        
        # Update syntax highlighting
        self._highlight_syntax(editor)
    
    def _start_auto_save(self):
        """Start the auto-save timer"""
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)
        
        self.auto_save_timer = self.root.after(self.auto_save_interval, self._auto_save)
    
    def _auto_save(self):
        """Automatically save the current file"""
        if self.text_modified and self.current_file:
            self._save_file()
            self.status_bar.config(text="Auto-saved: " + self.current_file)
        
        # Restart timer
        self._start_auto_save()
    
    def _new_project(self):
        """Create a new project"""
        if self.text_modified:
            if not messagebox.askyesno("Unsaved Changes", 
                                      "You have unsaved changes. Continue without saving?"):
                return
        
        # Get project directory
        project_dir = filedialog.askdirectory(title="Select Project Directory")
        if not project_dir:
            return
        
        # Create project structure
        try:
            self.project_dir = project_dir
            
            # Create directories
            directories = [
                "scripts",
                "resources/characters",
                "resources/backgrounds",
                "resources/music",
                "resources/sound",
                "versions"
            ]
            
            for directory in directories:
                os.makedirs(os.path.join(project_dir, directory), exist_ok=True)
            
            # Create basic project config
            self.project_config = {
                'name': os.path.basename(project_dir),
                'author': 'Unknown',
                'version': '0.1',
                'description': 'A visual novel project',
                'resources': {
                    'characters': {},
                    'backgrounds': {},
                    'music': {},
                    'sound': {}
                }
            }
            
            # Save project config
            with open(os.path.join(project_dir, "project.json"), 'w', encoding='utf-8') as f:
                json.dump(self.project_config, f, indent=2)
            
            # Create initial script file
            initial_script = (
                "# Main Script\n\n"
                "@scene:classroom\n\n"
                "@character:narrator\n"
                "This is the beginning of your visual novel adventure.\n\n"
                "@character:protagonist\n"
                "Hello, world! I'm ready to start my story.\n\n"
                "-> Continue the story\n"
                "-> End the story\n"
            )
            
            main_script_path = os.path.join(project_dir, "scripts", "main.vn")
            with open(main_script_path, 'w', encoding='utf-8') as f:
                f.write(initial_script)
            
            # Open the script
            self._open_file(main_script_path)
            
            # Refresh UI
            self._refresh_resources()
            self._refresh_characters()
            self._refresh_scenes()
            
            self.status_bar.config(text=f"New project created: {project_dir}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create project: {str(e)}")
    
    def _open_project(self):
        """Open an existing project"""
        if self.text_modified:
            if not messagebox.askyesno("Unsaved Changes", 
                                      "You have unsaved changes. Continue without saving?"):
                return
        
        # Get project directory
        project_dir = filedialog.askdirectory(title="Select Project Directory")
        if not project_dir:
            return
        
        # Check if it's a valid project
        project_config_path = os.path.join(project_dir, "project.json")
        if not os.path.exists(project_config_path):
            messagebox.showerror("Error", "Invalid project directory: Missing project.json")
            return
        
        try:
            # Load project config
            with open(project_config_path, 'r', encoding='utf-8') as f:
                self.project_config = json.load(f)
            
            self.project_dir = project_dir
            
            # Close all tabs
            for tab in self.editor_notebook.tabs():
                self.editor_notebook.forget(tab)
            
            # Find main script file
            script_dir = os.path.join(project_dir, "scripts")
            main_script_path = os.path.join(script_dir, "main.vn")
            
            if os.path.exists(main_script_path):
                self._open_file(main_script_path)
            else:
                # Find any script file
                script_files = [f for f in os.listdir(script_dir) if f.endswith(".vn")]
                if script_files:
                    self._open_file(os.path.join(script_dir, script_files[0]))
                else:
                    # Create a new empty tab
                    self._create_editor_tab("main.vn")
            
            # Refresh UI
            self._refresh_resources()
            self._refresh_characters()
            self._refresh_scenes()
            
            # Update window title
            self.root.title(f"VN Editor - {self.project_config['name']}")
            
            self.status_bar.config(text=f"Project opened: {project_dir}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open project: {str(e)}")
    
    def _save_project(self):
        """Save the current project configuration"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        try:
            # Save project config
            with open(os.path.join(self.project_dir, "project.json"), 'w', encoding='utf-8') as f:
                json.dump(self.project_config, f, indent=2)
            
            # Save any open files
            for tab_id in self.editor_notebook.tabs():
                tab_index = self.editor_notebook.index(tab_id)
                tab_frame = self.editor_notebook.winfo_children()[tab_index]
                
                if hasattr(tab_frame, 'file_path') and tab_frame.file_path:
                    try:
                        with open(tab_frame.file_path, 'w', encoding='utf-8') as f:
                            content = tab_frame.text_editor.get("1.0", tk.END)
                            f.write(content)
                        
                        # Update tab text to remove asterisk
                        tab_text = self.editor_notebook.tab(tab_id, "text")
                        if tab_text.endswith("*"):
                            self.editor_notebook.tab(tab_id, text=tab_text[:-1])
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to save file {tab_frame.file_path}: {str(e)}")
            
            self.status_bar.config(text=f"Project saved: {self.project_dir}")
            self.text_modified = False
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {str(e)}")
    
    def _project_settings(self):
        """Open project settings dialog"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Create dialog
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("Project Settings")
        settings_dialog.geometry("500x400")
        settings_dialog.transient(self.root)
        settings_dialog.grab_set()
        
        # Project info frame
        info_frame = ttk.LabelFrame(settings_dialog, text="Project Information")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Project name
        ttk.Label(info_frame, text="Project Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar(value=self.project_config.get('name', ''))
        ttk.Entry(info_frame, textvariable=name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Author
        ttk.Label(info_frame, text="Author:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        author_var = tk.StringVar(value=self.project_config.get('author', ''))
        ttk.Entry(info_frame, textvariable=author_var, width=30).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Version
        ttk.Label(info_frame, text="Version:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        version_var = tk.StringVar(value=self.project_config.get('version', '0.1'))
        ttk.Entry(info_frame, textvariable=version_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Description
        ttk.Label(info_frame, text="Description:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        description_text = tk.Text(info_frame, width=30, height=5)
        description_text.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        description_text.insert("1.0", self.project_config.get('description', ''))
        
        # Game settings frame
        game_frame = ttk.LabelFrame(settings_dialog, text="Game Settings")
        game_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Resolution
        ttk.Label(game_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        resolution_options = ["1280x720", "1920x1080", "800x600"]
        resolution_var = tk.StringVar(value=self.project_config.get('resolution', '1280x720'))
        ttk.Combobox(game_frame, textvariable=resolution_var, values=resolution_options).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Starting scene
        ttk.Label(game_frame, text="Starting Scene:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        start_scene_var = tk.StringVar(value=self.project_config.get('start_scene', 'main'))
        ttk.Entry(game_frame, textvariable=start_scene_var, width=20).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(settings_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_settings():
            # Save settings to project config
            self.project_config['name'] = name_var.get()
            self.project_config['author'] = author_var.get()
            self.project_config['version'] = version_var.get()
            self.project_config['description'] = description_text.get("1.0", tk.END).strip()
            self.project_config['resolution'] = resolution_var.get()
            self.project_config['start_scene'] = start_scene_var.get()
            
            # Save project
            self._save_project()
            
            # Update window title
            self.root.title(f"VN Editor - {self.project_config['name']}")
            
            settings_dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _new_file(self):
        """Create a new script file"""
        # Get file name
        file_name = simpledialog.askstring("New File", "Enter file name:")
        if not file_name:
            return
        
        # Add .vn extension if not present
        if not file_name.endswith(".vn"):
            file_name += ".vn"
        
        # Create a new editor tab
        self._create_editor_tab(file_name)
        
        self.status_bar.config(text="New file created")
    
    def _open_file(self, file_path=None):
        """Open a script file in the editor"""
        if not file_path:
            if self.project_dir:
                initial_dir = os.path.join(self.project_dir, "scripts")
            else:
                initial_dir = os.getcwd()
                
            file_path = filedialog.askopenfilename(
                title="Open Script File",
                initialdir=initial_dir,
                filetypes=[("Visual Novel Script", "*.vn"), ("Text Files", "*.txt"), ("All Files", "*.*")]
            )
        
        if not file_path:
            return
        
        try:
            # Check if the file is already open
            for tab_id in self.editor_notebook.tabs():
                tab_index = self.editor_notebook.index(tab_id)
                tab_frame = self.editor_notebook.winfo_children()[tab_index]
                
                if hasattr(tab_frame, 'file_path') and tab_frame.file_path == file_path:
                    self.editor_notebook.select(tab_id)
                    return
            
            # Open the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create a new tab for this file
            file_name = os.path.basename(file_path)
            text_editor = self._create_editor_tab(file_name, content)
            
            # Store file path
            current_tab = self.editor_notebook.select()
            tab_index = self.editor_notebook.index(current_tab)
            tab_frame = self.editor_notebook.winfo_children()[tab_index]
            tab_frame.file_path = file_path
            
            # Set as current file
            self.current_file = file_path
            
            # Reset modified flag
            self.text_modified = False
            
            self.status_bar.config(text=f"Opened: {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")
    
    def _save_file(self):
        """Save the current file"""
        current_tab = self.editor_notebook.select()
        if not current_tab:
            return False
            
        tab_index = self.editor_notebook.index(current_tab)
        tab_frame = self.editor_notebook.winfo_children()[tab_index]
        
        # If file has not been saved before, use Save As
        if not hasattr(tab_frame, 'file_path') or not tab_frame.file_path:
            return self._save_file_as()
        
        try:
            # Get content from the editor
            content = tab_frame.text_editor.get("1.0", tk.END)
            
            # Save the file
            with open(tab_frame.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update tab text to remove asterisk
            tab_text = self.editor_notebook.tab(current_tab, "text")
            if tab_text.endswith("*"):
                self.editor_notebook.tab(current_tab, text=tab_text[:-1])
            
            # Update status
            self.status_bar.config(text=f"Saved: {tab_frame.file_path}")
            self.text_modified = False
            
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            return False
    
    def _save_file_as(self):
        """Save the current file with a new name"""
        current_tab = self.editor_notebook.select()
        if not current_tab:
            return False
            
        tab_index = self.editor_notebook.index(current_tab)
        tab_frame = self.editor_notebook.winfo_children()[tab_index]
        
        # Get file path
        if self.project_dir:
            initial_dir = os.path.join(self.project_dir, "scripts")
        else:
            initial_dir = os.getcwd()
            
        file_path = filedialog.asksaveasfilename(
            title="Save Script File",
            initialdir=initial_dir,
            defaultextension=".vn",
            filetypes=[("Visual Novel Script", "*.vn"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return False
        
        # Update file path
        tab_frame.file_path = file_path
        
        # Update tab text
        file_name = os.path.basename(file_path)
        self.editor_notebook.tab(current_tab, text=file_name)
        
        # Set as current file
        self.current_file = file_path
        
        # Save the file
        return self._save_file()
    
    def _insert_character_dialogue(self):
        """Insert character dialogue at the cursor position"""
        editor = self._get_current_editor()
        if not editor:
            return
        
        # Get available characters
        characters = self._get_available_characters()
        
        if not characters:
            messagebox.showinfo("Character Dialogue", "No characters available. Create a character first.")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Insert Character Dialogue")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Character selection
        ttk.Label(dialog, text="Character:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        character_var = tk.StringVar()
        character_dropdown = ttk.Combobox(dialog, textvariable=character_var, values=characters)
        character_dropdown.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        if characters:
            character_dropdown.set(characters[0])
        
        # Dialogue text
        ttk.Label(dialog, text="Dialogue:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
        dialogue_text = tk.Text(dialog, width=40, height=5)
        dialogue_text.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        def insert_dialogue():
            character = character_var.get()
            dialogue = dialogue_text.get("1.0", tk.END).strip()
            
            if character and dialogue:
                # Format: @character:name\nDialogue text
                formatted = f"@character:{character}\n{dialogue}\n\n"
                editor.insert(tk.INSERT, formatted)
                self._highlight_syntax(editor)
                editor.see(tk.INSERT)
                editor.update_idletasks()
                dialog.destroy()
        
        ttk.Button(button_frame, text="Insert", command=insert_dialogue).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _insert_character_expression(self):
        """Insert character expression at the cursor position"""
        editor = self._get_current_editor()
        if not editor:
            return
        
        # Get available characters
        characters = self._get_available_characters()
        
        if not characters:
            messagebox.showinfo("Character Expression", "No characters available. Create a character first.")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Insert Character Expression")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Character selection
        ttk.Label(dialog, text="Character:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        character_var = tk.StringVar()
        character_dropdown = ttk.Combobox(dialog, textvariable=character_var, values=characters)
        character_dropdown.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        if characters:
            character_dropdown.set(characters[0])
        
        # Expression options
        expressions = ["happy", "sad", "angry", "surprised", "neutral"]
        
        ttk.Label(dialog, text="Expression:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        expression_var = tk.StringVar()
        expression_dropdown = ttk.Combobox(dialog, textvariable=expression_var, values=expressions)
        expression_dropdown.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        expression_dropdown.set("neutral")
        
        # Dialogue text
        ttk.Label(dialog, text="Dialogue:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        dialogue_text = tk.Text(dialog, width=40, height=5)
        dialogue_text.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        def insert_expression():
            character = character_var.get()
            expression = expression_var.get()
            dialogue = dialogue_text.get("1.0", tk.END).strip()
            
            if character and expression and dialogue:
                # Format: @character:name:expression\nDialogue text
                formatted = f"@{character}:{expression}\n{dialogue}\n\n"
                editor.insert(tk.INSERT, formatted)
                self._highlight_syntax(editor)
                editor.see(tk.INSERT)
                editor.update_idletasks()
                dialog.destroy()
        
        ttk.Button(button_frame, text="Insert", command=insert_expression).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _insert_choice(self):
        """Insert choice options at the cursor position"""
        editor = self._get_current_editor()
        if not editor:
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Insert Choices")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Choice prompt
        ttk.Label(dialog, text="Prompt:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        prompt_entry = ttk.Entry(dialog, width=40)
        prompt_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Choices
        ttk.Label(dialog, text="Choices:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
        choices_frame = ttk.Frame(dialog)
        choices_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        choice_entries = []
        
        def add_choice_entry():
            entry = ttk.Entry(choices_frame, width=40)
            entry.pack(fill=tk.X, pady=2)
            choice_entries.append(entry)
        
        # Add initial choices
        for _ in range(2):
            add_choice_entry()
        
        # Add button
        ttk.Button(choices_frame, text="Add Choice", command=add_choice_entry).pack(anchor=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        def insert_choices():
            prompt = prompt_entry.get().strip()
            choices = [entry.get().strip() for entry in choice_entries if entry.get().strip()]
            
            if not choices:
                messagebox.showwarning("No Choices", "Please add at least one choice.")
                return
            
            # Format output
            if prompt:
                formatted = f"{prompt}\n\n"
            else:
                formatted = ""
                
            for choice in choices:
                formatted += f"-> {choice}\n"
            
            formatted += "\n"
            editor.insert(tk.INSERT, formatted)
            self._highlight_syntax(editor)
            editor.see(tk.INSERT)
            editor.update_idletasks()
            dialog.destroy()
        
        ttk.Button(button_frame, text="Insert", command=insert_choices).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _insert_scene(self):
        """Insert scene change at the cursor position"""
        editor = self._get_current_editor()
        if not editor:
            return
        
        # Get available backgrounds
        backgrounds = self._get_available_backgrounds()
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Insert Scene")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Scene name
        ttk.Label(dialog, text="Scene Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        scene_var = tk.StringVar()
        
        if backgrounds:
            scene_entry = ttk.Combobox(dialog, textvariable=scene_var, values=backgrounds)
            scene_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            scene_entry.set(backgrounds[0])
        else:
            scene_entry = ttk.Entry(dialog, textvariable=scene_var, width=30)
            scene_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Transition
        ttk.Label(dialog, text="Transition:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        transitions = ["none", "fade", "dissolve", "slide_left", "slide_right"]
        transition_var = tk.StringVar(value="fade")
        transition_dropdown = ttk.Combobox(dialog, textvariable=transition_var, values=transitions)
        transition_dropdown.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Description
        ttk.Label(dialog, text="Description:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        description_text = tk.Text(dialog, width=40, height=3)
        description_text.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        def insert_scene():
            scene = scene_var.get().strip()
            transition = transition_var.get()
            description = description_text.get("1.0", tk.END).strip()
            
            if scene:
                # Format: @scene:name:transition\nDescription
                if transition and transition != "none":
                    formatted = f"@scene:{scene}:{transition}\n"
                else:
                    formatted = f"@scene:{scene}\n"
                    
                if description:
                    formatted += f"# {description}\n"
                    
                formatted += "\n"
                editor.insert(tk.INSERT, formatted)
                self._highlight_syntax(editor)
                editor.see(tk.INSERT)
                editor.update_idletasks()
                dialog.destroy()
        
        ttk.Button(button_frame, text="Insert", command=insert_scene).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _insert_bgm(self):
        """Insert background music at the cursor position"""
        editor = self._get_current_editor()
        if not editor:
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Insert Background Music")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Get available music
        music_files = self._get_available_music()
        
        # BGM name
        ttk.Label(dialog, text="Music:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        bgm_var = tk.StringVar()
        
        if music_files:
            bgm_entry = ttk.Combobox(dialog, textvariable=bgm_var, values=music_files)
            bgm_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            bgm_entry.set(music_files[0])
        else:
            bgm_entry = ttk.Entry(dialog, textvariable=bgm_var, width=30)
            bgm_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Fade in
        ttk.Label(dialog, text="Fade In (seconds):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        fade_var = tk.StringVar(value="1.0")
        ttk.Entry(dialog, textvariable=fade_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Loop
        loop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Loop", variable=loop_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        def insert_bgm():
            bgm = bgm_var.get().strip()
            fade = fade_var.get().strip()
            loop = loop_var.get()
            
            if bgm:
                # Format: @bgm:name:fade:loop
                formatted = f"@bgm:{bgm}"
                
                if fade and fade != "0":
                    formatted += f":{fade}"
                
                if not loop:
                    formatted += ":noloop"
                
                formatted += "\n\n"
                editor.insert(tk.INSERT, formatted)
                self._highlight_syntax(editor)
                editor.see(tk.INSERT)
                editor.update_idletasks()
                dialog.destroy()
        
        ttk.Button(button_frame, text="Insert", command=insert_bgm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _insert_sound(self):
        """Insert sound effect at the cursor position"""
        editor = self._get_current_editor()
        if not editor:
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Insert Sound Effect")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Get available sound effects
        sound_files = self._get_available_sounds()
        
        # Sound name
        ttk.Label(dialog, text="Sound Effect:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        sound_var = tk.StringVar()
        
        if sound_files:
            sound_entry = ttk.Combobox(dialog, textvariable=sound_var, values=sound_files)
            sound_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            sound_entry.set(sound_files[0])
        else:
            sound_entry = ttk.Entry(dialog, textvariable=sound_var, width=30)
            sound_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Volume
        ttk.Label(dialog, text="Volume (0-100):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        volume_var = tk.StringVar(value="100")
        ttk.Entry(dialog, textvariable=volume_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        def insert_sound():
            sound = sound_var.get().strip()
            volume = volume_var.get().strip()
            
            if sound:
                # Format: @sound:name:volume
                formatted = f"@sound:{sound}"
                
                if volume and volume != "100":
                    formatted += f":{volume}"
                
                formatted += "\n\n"
                editor.insert(tk.INSERT, formatted)
                self._highlight_syntax(editor)
                editor.see(tk.INSERT)
                editor.update_idletasks()
                dialog.destroy()
        
        ttk.Button(button_frame, text="Insert", command=insert_sound).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _format_text(self, prefix, suffix):
        """Apply formatting to selected text or insert formatting markers"""
        editor = self._get_current_editor()
        if not editor:
            return
        
        # Check if there is selected text
        try:
            selected_text = editor.get(tk.SEL_FIRST, tk.SEL_LAST)
            editor.delete(tk.SEL_FIRST, tk.SEL_LAST)
            editor.insert(tk.INSERT, f"{prefix}{selected_text}{suffix}")
        except tk.TclError:
            # No selection, just insert the markers
            editor.insert(tk.INSERT, f"{prefix}{suffix}")
            
            # Move cursor between the markers
            cursor_pos = editor.index(tk.INSERT)
            line, col = cursor_pos.split('.')
            new_pos = f"{line}.{int(col) - len(suffix)}"
            editor.mark_set(tk.INSERT, new_pos)
    
    def _get_available_characters(self):
        """Get a list of available character names"""
        if not self.project_dir:
            return []
            
        characters = []
        
        # Check project config
        if 'resources' in self.project_config and 'characters' in self.project_config['resources']:
            characters.extend(self.project_config['resources']['characters'].keys())
        
        # Check characters directory
        char_dir = os.path.join(self.project_dir, "resources", "characters")
        if os.path.exists(char_dir):
            for item in os.listdir(char_dir):
                if os.path.isdir(os.path.join(char_dir, item)) and item not in characters:
                    characters.append(item)
        
        # Add some defaults if no characters found
        if not characters:
            characters = ["protagonist", "narrator"]
        
        return characters
    
    def _get_available_backgrounds(self):
        """Get a list of available background names"""
        if not self.project_dir:
            return []
            
        backgrounds = []
        
        # Check project config
        if 'resources' in self.project_config and 'backgrounds' in self.project_config['resources']:
            backgrounds.extend(self.project_config['resources']['backgrounds'].keys())
        
        # Check backgrounds directory
        bg_dir = os.path.join(self.project_dir, "resources", "backgrounds")
        if os.path.exists(bg_dir):
            for item in os.listdir(bg_dir):
                if item.endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    name = os.path.splitext(item)[0]
                    if name not in backgrounds:
                        backgrounds.append(name)
        
        # Add some defaults if no backgrounds found
        if not backgrounds:
            backgrounds = ["classroom", "street", "house"]
        
        return backgrounds
    
    def _get_available_music(self):
        """Get a list of available music names"""
        if not self.project_dir:
            return []
            
        music_files = []
        
        # Check project config
        if 'resources' in self.project_config and 'music' in self.project_config['resources']:
            music_files.extend(self.project_config['resources']['music'].keys())
        
        # Check music directory
        music_dir = os.path.join(self.project_dir, "resources", "music")
        if os.path.exists(music_dir):
            for item in os.listdir(music_dir):
                if item.endswith(('.ogg', '.mp3', '.wav')):
                    name = os.path.splitext(item)[0]
                    if name not in music_files:
                        music_files.append(name)
        
        return music_files
    
    def _get_available_sounds(self):
        """Get a list of available sound effect names"""
        if not self.project_dir:
            return []
            
        sound_files = []
        
        # Check project config
        if 'resources' in self.project_config and 'sound' in self.project_config['resources']:
            sound_files.extend(self.project_config['resources']['sound'].keys())
        
        # Check sound directory
        sound_dir = os.path.join(self.project_dir, "resources", "sound")
        if os.path.exists(sound_dir):
            for item in os.listdir(sound_dir):
                if item.endswith(('.ogg', '.mp3', '.wav')):
                    name = os.path.splitext(item)[0]
                    if name not in sound_files:
                        sound_files.append(name)
        
        return sound_files
    
    def _insert_selected_character(self, event):
        """Insert the selected character into the editor"""
        selected_item = self.characters_tree.focus()
        if not selected_item:
            return
            
        character = self.characters_tree.item(selected_item, "text")
        if character:
            editor = self._get_current_editor()
            if editor:
                editor.insert(tk.INSERT, f"@character:{character}\n")
    
    def _insert_selected_scene(self, event):
        """Insert the selected scene into the editor"""
        selected_item = self.scenes_tree.focus()
        if not selected_item:
            return
            
        scene = self.scenes_tree.item(selected_item, "text")
        if scene:
            editor = self._get_current_editor()
            if editor:
                editor.insert(tk.INSERT, f"@scene:{scene}\n")
    
    def _insert_selected_resource(self, event):
        """Insert the selected resource into the editor"""
        selected_item = self.resources_tree.focus()
        if not selected_item:
            return
            
        resource = self.resources_tree.item(selected_item, "text")
        parent = self.resources_tree.parent(selected_item)
        
        if not parent:
            return  # This is a category, not a resource
            
        category = self.resources_tree.item(parent, "text")
        
        editor = self._get_current_editor()
        if not editor:
            return
            
        if category == "Backgrounds":
            editor.insert(tk.INSERT, f"@scene:{resource}\n")
        elif category == "Characters":
            editor.insert(tk.INSERT, f"@character:{resource}\n")
        elif category == "Music":
            editor.insert(tk.INSERT, f"@bgm:{resource}\n")
        elif category == "Sound Effects":
            editor.insert(tk.INSERT, f"@sound:{resource}\n")
    
    def _show_search_dialog(self):
        """Show the search dialog"""
        editor = self._get_current_editor()
        if not editor:
            return
            
        if self.search_dialog:
            self.search_dialog.destroy()
            
        self.search_dialog = tk.Toplevel(self.root)
        self.search_dialog.title("Find")
        self.search_dialog.transient(self.root)
        self.search_dialog.resizable(False, False)
        
        ttk.Label(self.search_dialog, text="Find:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        search_entry = ttk.Entry(self.search_dialog, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        search_entry.focus_set()
        
        # Search options
        options_frame = ttk.Frame(self.search_dialog)
        options_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        case_sensitive = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Case sensitive", variable=case_sensitive).pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(self.search_dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        def find_next():
            """Find the next occurrence of the search text"""
            search_text = self.search_var.get()
            if not search_text:
                return
                
            # Get current cursor position
            start_pos = editor.index(tk.INSERT)
            
            # Search from cursor to end
            text_content = editor.get(start_pos, tk.END)
            if not case_sensitive.get():
                text_content = text_content.lower()
                search_text = search_text.lower()
                
            pos = text_content.find(search_text)
            
            if pos >= 0:
                # Calculate absolute position
                line, col = start_pos.split('.')
                start_index = f"{line}.{int(col) + pos}"
                end_index = f"{line}.{int(col) + pos + len(search_text)}"
                
                # Select the found text
                editor.tag_remove(tk.SEL, "1.0", tk.END)
                editor.tag_add(tk.SEL, start_index, end_index)
                editor.see(start_index)
                editor.mark_set(tk.INSERT, end_index)
            else:
                # Try from beginning
                text_content = editor.get("1.0", tk.END)
                if not case_sensitive.get():
                    text_content = text_content.lower()
                    
                pos = text_content.find(search_text)
                
                if pos >= 0:
                    # Find line and column
                    lines = text_content[:pos].split('\n')
                    line = len(lines)
                    col = len(lines[-1]) if lines else 0
                    
                    start_index = f"{line}.{col}"
                    end_index = f"{line}.{col + len(search_text)}"
                    
                    # Select the found text
                    editor.tag_remove(tk.SEL, "1.0", tk.END)
                    editor.tag_add(tk.SEL, start_index, end_index)
                    editor.see(start_index)
                    editor.mark_set(tk.INSERT, end_index)
                else:
                    messagebox.showinfo("Search", f"Cannot find '{search_text}'")
        
        ttk.Button(button_frame, text="Find Next", command=find_next).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.search_dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_replace_dialog(self):
        """Show the replace dialog"""
        editor = self._get_current_editor()
        if not editor:
            return
            
        if self.search_dialog:
            self.search_dialog.destroy()
            
        self.search_dialog = tk.Toplevel(self.root)
        self.search_dialog.title("Replace")
        self.search_dialog.transient(self.root)
        self.search_dialog.resizable(False, False)
        
        ttk.Label(self.search_dialog, text="Find:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        search_entry = ttk.Entry(self.search_dialog, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        search_entry.focus_set()
        
        ttk.Label(self.search_dialog, text="Replace with:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        replace_entry = ttk.Entry(self.search_dialog, textvariable=self.replace_var, width=30)
        replace_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Search options
        options_frame = ttk.Frame(self.search_dialog)
        options_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        case_sensitive = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Case sensitive", variable=case_sensitive).pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(self.search_dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        def find_next():
            """Find the next occurrence of the search text"""
            search_text = self.search_var.get()
            if not search_text:
                return
                
            # Get current cursor position
            start_pos = editor.index(tk.INSERT)
            
            # Search from cursor to end
            text_content = editor.get(start_pos, tk.END)
            if not case_sensitive.get():
                search_content = text_content.lower()
                search_term = search_text.lower()
            else:
                search_content = text_content
                search_term = search_text
                
            pos = search_content.find(search_term)
            
            if pos >= 0:
                # Calculate absolute position
                line, col = start_pos.split('.')
                start_index = f"{line}.{int(col) + pos}"
                end_index = f"{line}.{int(col) + pos + len(search_text)}"
                
                # Select the found text
                editor.tag_remove(tk.SEL, "1.0", tk.END)
                editor.tag_add(tk.SEL, start_index, end_index)
                editor.see(start_index)
                editor.mark_set(tk.INSERT, end_index)
                return True
            else:
                # Try from beginning
                text_content = editor.get("1.0", tk.END)
                if not case_sensitive.get():
                    search_content = text_content.lower()
                else:
                    search_content = text_content
                    
                pos = search_content.find(search_term)
                
                if pos >= 0:
                    # Find line and column
                    lines = text_content[:pos].split('\n')
                    line = len(lines)
                    col = len(lines[-1]) if lines else 0
                    
                    start_index = f"{line}.{col}"
                    end_index = f"{line}.{col + len(search_text)}"
                    
                    # Select the found text
                    editor.tag_remove(tk.SEL, "1.0", tk.END)
                    editor.tag_add(tk.SEL, start_index, end_index)
                    editor.see(start_index)
                    editor.mark_set(tk.INSERT, end_index)
                    return True
                else:
                    messagebox.showinfo("Search", f"Cannot find '{search_text}'")
                    return False
        
        def replace():
            """Replace the selected text"""
            try:
                selected_text = editor.get(tk.SEL_FIRST, tk.SEL_LAST)
                if (not case_sensitive.get() and selected_text.lower() == self.search_var.get().lower()) or \
                   (case_sensitive.get() and selected_text == self.search_var.get()):
                    editor.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    editor.insert(tk.INSERT, self.replace_var.get())
                    
                # Find next occurrence
                find_next()
            except tk.TclError:
                # No selection, find next
                find_next()
        
        def replace_all():
            """Replace all occurrences of the search text"""
            search_text = self.search_var.get()
            replace_text = self.replace_var.get()
            
            if not search_text:
                return
                
            # Start from the beginning
            editor.mark_set(tk.INSERT, "1.0")
            
            count = 0
            while find_next():
                try:
                    editor.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    editor.insert(tk.INSERT, replace_text)
                    count += 1
                except tk.TclError:
                    break
            
            messagebox.showinfo("Replace", f"Replaced {count} occurrences")
        
        ttk.Button(button_frame, text="Find Next", command=find_next).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Replace", command=replace).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Replace All", command=replace_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.search_dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _undo(self):
        """Undo last edit operation"""
        editor = self._get_current_editor()
        if editor:
            try:
                editor.edit_undo()
            except tk.TclError:
                # Nothing to undo
                pass
    
    def _redo(self):
        """Redo last undone edit operation"""
        editor = self._get_current_editor()
        if editor:
            try:
                editor.edit_redo()
            except tk.TclError:
                # Nothing to redo
                pass
    
    def _cut(self):
        """Cut selected text to clipboard"""
        editor = self._get_current_editor()
        if editor:
            try:
                # Check if there is a selection
                selected = editor.get(tk.SEL_FIRST, tk.SEL_LAST)
                editor.clipboard_clear()
                editor.clipboard_append(selected)
                editor.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                # No selection
                pass
    
    def _copy(self):
        """Copy selected text to clipboard"""
        editor = self._get_current_editor()
        if editor:
            try:
                # Check if there is a selection
                selected = editor.get(tk.SEL_FIRST, tk.SEL_LAST)
                editor.clipboard_clear()
                editor.clipboard_append(selected)
            except tk.TclError:
                # No selection
                pass
    
    def _paste(self):
        """Paste text from clipboard"""
        editor = self._get_current_editor()
        if editor:
            try:
                text = editor.clipboard_get()
                if text:
                    # Delete selected text if any
                    try:
                        editor.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    except tk.TclError:
                        pass
                    
                    editor.insert(tk.INSERT, text)
            except tk.TclError:
                # Nothing in clipboard
                pass
    
    def _add_character(self):
        """Add a new character to the project"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Character")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Character info
        ttk.Label(dialog, text="Character Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="Display Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        display_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=display_var, width=30).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="Description:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        description_text = tk.Text(dialog, width=30, height=3)
        description_text.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Expressions
        ttk.Label(dialog, text="Expressions:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        expressions_frame = ttk.Frame(dialog)
        expressions_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        expression_entries = []
        
        def add_expression_entry():
            frame = ttk.Frame(expressions_frame)
            frame.pack(fill=tk.X, pady=2)
            
            name_var = tk.StringVar()
            ttk.Label(frame, text="Name:").pack(side=tk.LEFT)
            ttk.Entry(frame, textvariable=name_var, width=10).pack(side=tk.LEFT, padx=2)
            
            file_var = tk.StringVar()
            ttk.Label(frame, text="File:").pack(side=tk.LEFT, padx=(5, 0))
            file_entry = ttk.Entry(frame, textvariable=file_var, width=15)
            file_entry.pack(side=tk.LEFT, padx=2)
            
            def browse_file():
                file_path = filedialog.askopenfilename(
                    title="Select Image",
                    filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")]
                )
                if file_path:
                    file_var.set(os.path.basename(file_path))
            
            ttk.Button(frame, text="...", width=3, command=browse_file).pack(side=tk.LEFT, padx=2)
            
            expression_entries.append((name_var, file_var))
        
        # Add initial expressions
        add_expression_entry()  # neutral
        add_expression_entry()  # happy
        
        ttk.Button(expressions_frame, text="Add Expression", command=add_expression_entry).pack(anchor=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        def save_character():
            nonlocal name_var
            character_name = name_var.get().strip()
            if not character_name:
                messagebox.showwarning("Warning", "Character name is required")
                return
                
            # Create character directory
            char_dir = os.path.join(self.project_dir, "resources", "characters", character_name)
            os.makedirs(char_dir, exist_ok=True)
            
            # Create character info file
            char_info = {
                "name": character_name,
                "display_name": display_var.get().strip() or character_name,
                "description": description_text.get("1.0", tk.END).strip(),
                "expressions": {}
            }
            
            # Process expressions
            for name_var, file_var in expression_entries:
                expr_name = name_var.get().strip()
                expr_file = file_var.get().strip()
                
                if expr_name and expr_file:
                    char_info["expressions"][expr_name] = expr_file
            
            # Save character info
            with open(os.path.join(char_dir, "character.json"), 'w', encoding='utf-8') as f:
                json.dump(char_info, f, indent=2)
            
            # Update project config
            if 'resources' not in self.project_config:
                self.project_config['resources'] = {}
                
            if 'characters' not in self.project_config['resources']:
                self.project_config['resources']['characters'] = {}
                
            self.project_config['resources']['characters'][character_name] = {
                "dir": os.path.join("resources", "characters", character_name),
                "info": os.path.join("resources", "characters", character_name, "character.json")
            }
            
            # Save project config
            self._save_project()
            
            # Refresh characters
            self._refresh_characters()
            
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _edit_character(self):
        """Edit an existing character"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
            
        # Get selected character
        selected_item = self.characters_tree.focus()
        if not selected_item:
            messagebox.showinfo("Edit Character", "Please select a character to edit")
            return
            
        character_name = self.characters_tree.item(selected_item, "text")
        
        # Check if character exists
        char_dir = os.path.join(self.project_dir, "resources", "characters", character_name)
        if not os.path.exists(char_dir):
            messagebox.showerror("Error", f"Character directory not found: {char_dir}")
            return
            
        char_info_file = os.path.join(char_dir, "character.json")
        
        try:
            # Load character info
            if os.path.exists(char_info_file):
                with open(char_info_file, 'r', encoding='utf-8') as f:
                    char_info = json.load(f)
            else:
                char_info = {
                    "name": character_name,
                    "display_name": character_name,
                    "description": "",
                    "expressions": {}
                }
                
            # Create dialog
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Edit Character: {character_name}")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Character info
            ttk.Label(dialog, text="Character Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            name_var = tk.StringVar(value=char_info["name"])
            ttk.Entry(dialog, textvariable=name_var, width=30, state="readonly").grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            ttk.Label(dialog, text="Display Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
            display_var = tk.StringVar(value=char_info.get("display_name", character_name))
            ttk.Entry(dialog, textvariable=display_var, width=30).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
            
            ttk.Label(dialog, text="Description:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
            description_text = tk.Text(dialog, width=30, height=3)
            description_text.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
            description_text.insert("1.0", char_info.get("description", ""))
            
            # Expressions
            ttk.Label(dialog, text="Expressions:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
            expressions_frame = ttk.Frame(dialog)
            expressions_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
            
            expression_entries = []
            
            def add_expression_entry(name="", file=""):
                frame = ttk.Frame(expressions_frame)
                frame.pack(fill=tk.X, pady=2)
                
                name_var = tk.StringVar(value=name)
                ttk.Label(frame, text="Name:").pack(side=tk.LEFT)
                ttk.Entry(frame, textvariable=name_var, width=10).pack(side=tk.LEFT, padx=2)
                
                file_var = tk.StringVar(value=file)
                ttk.Label(frame, text="File:").pack(side=tk.LEFT, padx=(5, 0))
                file_entry = ttk.Entry(frame, textvariable=file_var, width=15)
                file_entry.pack(side=tk.LEFT, padx=2)
                
                def browse_file():
                    file_path = filedialog.askopenfilename(
                        title="Select Image",
                        filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")]
                    )
                    if file_path:
                        file_var.set(os.path.basename(file_path))
                
                ttk.Button(frame, text="...", width=3, command=browse_file).pack(side=tk.LEFT, padx=2)
                
                expression_entries.append((name_var, file_var))
            
            # Add existing expressions
            for expr_name, expr_file in char_info.get("expressions", {}).items():
                add_expression_entry(expr_name, expr_file)
            
            # Add default expressions if none exist
            if not char_info.get("expressions"):
                add_expression_entry("neutral", "")
                add_expression_entry("happy", "")
            
            ttk.Button(expressions_frame, text="Add Expression", command=lambda: add_expression_entry()).pack(anchor=tk.W, pady=5)
            
            # Buttons
            button_frame = ttk.Frame(dialog)
            button_frame.grid(row=4, column=0, columnspan=2, pady=10)
            
            def save_character():
                # Update character info
                char_info["display_name"] = display_var.get().strip() or character_name
                char_info["description"] = description_text.get("1.0", tk.END).strip()
                
                # Update expressions
                char_info["expressions"] = {}
                for name_var, file_var in expression_entries:
                    expr_name = name_var.get().strip()
                    expr_file = file_var.get().strip()
                    
                    if expr_name and expr_file:
                        char_info["expressions"][expr_name] = expr_file
                
                # Save character info
                with open(char_info_file, 'w', encoding='utf-8') as f:
                    json.dump(char_info, f, indent=2)
                
                # Refresh characters
                self._refresh_characters()
                
                dialog.destroy()
            
            ttk.Button(button_frame, text="Save", command=save_character).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit character: {str(e)}")
    
    def _remove_character(self):
        """Remove a character from the project"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
            
        # Get selected character
        selected_item = self.characters_tree.focus()
        if not selected_item:
            messagebox.showinfo("Remove Character", "Please select a character to remove")
            return
            
        character_name = self.characters_tree.item(selected_item, "text")
        
        # Confirm deletion
        if not messagebox.askyesno("Remove Character", 
                                   f"Are you sure you want to remove the character '{character_name}'?\n"
                                   "This will delete all character files and references."):
            return
        
        try:
            # Remove character directory
            char_dir = os.path.join(self.project_dir, "resources", "characters", character_name)
            if os.path.exists(char_dir):
                shutil.rmtree(char_dir)
            
            # Remove from project config
            if 'resources' in self.project_config and 'characters' in self.project_config['resources'] \
               and character_name in self.project_config['resources']['characters']:
                del self.project_config['resources']['characters'][character_name]
            
            # Save project config
            self._save_project()
            
            # Refresh characters
            self._refresh_characters()
            
            messagebox.showinfo("Remove Character", f"Character '{character_name}' removed successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove character: {str(e)}")
    
    def _refresh_characters(self):
        """Refresh the characters list"""
        # Clear the treeview
        for item in self.characters_tree.get_children():
            self.characters_tree.delete(item)
        
        if not self.project_dir:
            return
        
        # Add characters from project config
        if 'resources' in self.project_config and 'characters' in self.project_config['resources']:
            for char_name, char_data in self.project_config['resources']['characters'].items():
                # Try to load character info
                try:
                    char_info_file = os.path.join(self.project_dir, char_data.get("info", ""))
                    if os.path.exists(char_info_file):
                        with open(char_info_file, 'r', encoding='utf-8') as f:
                            char_info = json.load(f)
                        
                        expressions = ", ".join(char_info.get("expressions", {}).keys())
                        self.characters_tree.insert("", "end", text=char_name, values=(expressions,))
                    else:
                        self.characters_tree.insert("", "end", text=char_name, values=("No info file",))
                except Exception as e:
                    self.characters_tree.insert("", "end", text=char_name, values=(f"Error: {str(e)}",))
        
        # Check characters directory for additional characters
        char_dir = os.path.join(self.project_dir, "resources", "characters")
        if os.path.exists(char_dir):
            for item in os.listdir(char_dir):
                # Skip if already in treeview
                found = False
                for existing in self.characters_tree.get_children():
                    if self.characters_tree.item(existing, "text") == item:
                        found = True
                        break
                
                if found:
                    continue
                
                # Check if it's a directory
                if os.path.isdir(os.path.join(char_dir, item)):
                    # Try to load character info
                    try:
                        char_info_file = os.path.join(char_dir, item, "character.json")
                        if os.path.exists(char_info_file):
                            with open(char_info_file, 'r', encoding='utf-8') as f:
                                char_info = json.load(f)
                            
                            expressions = ", ".join(char_info.get("expressions", {}).keys())
                            self.characters_tree.insert("", "end", text=item, values=(expressions,))
                        else:
                            # Just add the character without expressions
                            self.characters_tree.insert("", "end", text=item, values=("No info file",))
                    except Exception as e:
                        self.characters_tree.insert("", "end", text=item, values=(f"Error: {str(e)}",))
    
    def _add_scene(self):
        """Add a new scene to the project"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Scene")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Scene info
        ttk.Label(dialog, text="Scene ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        id_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=id_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="Scene Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="Background:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        background_frame = ttk.Frame(dialog)
        background_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        background_var = tk.StringVar()
        background_entry = ttk.Entry(background_frame, textvariable=background_var, width=20)
        background_entry.pack(side=tk.LEFT)
        
        def browse_background():
            file_path = filedialog.askopenfilename(
                title="Select Background Image",
                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")]
            )
            if file_path:
                background_var.set(os.path.basename(file_path))
        
        ttk.Button(background_frame, text="...", width=3, command=browse_background).pack(side=tk.LEFT, padx=2)
        
        # Description
        ttk.Label(dialog, text="Description:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        description_text = tk.Text(dialog, width=30, height=5)
        description_text.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Script file
        ttk.Label(dialog, text="Script File:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        script_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=script_var, width=30).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        def save_scene():
            scene_id = id_var.get().strip()
            if not scene_id:
                messagebox.showwarning("Warning", "Scene ID is required")
                return
            
            # Add to project config
            if 'scenes' not in self.project_config:
                self.project_config['scenes'] = {}
                
            self.project_config['scenes'][scene_id] = {
                "name": name_var.get().strip() or scene_id,
                "description": description_text.get("1.0", tk.END).strip(),
                "background": background_var.get().strip(),
                "script": script_var.get().strip() or f"{scene_id}.vn"
            }
            
            # Copy background image if provided
            background = background_var.get().strip()
            if background:
                src_path = os.path.join(os.path.dirname(background_var.get()), background)
                if os.path.exists(src_path):
                    dst_path = os.path.join(self.project_dir, "resources", "backgrounds", background)
                    shutil.copy(src_path, dst_path)
            
            # Create script file if it doesn't exist
            script_file = script_var.get().strip() or f"{scene_id}.vn"
            script_path = os.path.join(self.project_dir, "scripts", script_file)
            
            if not os.path.exists(script_path):
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Scene: {scene_id}\n\n@scene:{scene_id}\n\n")
            
            # Save project
            self._save_project()
            
            # Refresh scenes
            self._refresh_scenes()
            
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_scene).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _edit_scene(self):
        """Edit an existing scene"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
            
        # Get selected scene
        selected_item = self.scenes_tree.focus()
        if not selected_item:
            messagebox.showinfo("Edit Scene", "Please select a scene to edit")
            return
            
        scene_id = self.scenes_tree.item(selected_item, "text")
        
        # Check if scene exists
        if 'scenes' not in self.project_config or scene_id not in self.project_config['scenes']:
            messagebox.showerror("Error", f"Scene not found in project config: {scene_id}")
            return
            
        scene_data = self.project_config['scenes'][scene_id]
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Scene: {scene_id}")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Scene info
        ttk.Label(dialog, text="Scene ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        id_var = tk.StringVar(value=scene_id)
        ttk.Entry(dialog, textvariable=id_var, width=30, state="readonly").grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="Scene Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar(value=scene_data.get("name", scene_id))
        ttk.Entry(dialog, textvariable=name_var, width=30).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="Background:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        background_frame = ttk.Frame(dialog)
        background_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        background_var = tk.StringVar(value=scene_data.get("background", ""))
        background_entry = ttk.Entry(background_frame, textvariable=background_var, width=20)
        background_entry.pack(side=tk.LEFT)
        
        def browse_background():
            file_path = filedialog.askopenfilename(
                title="Select Background Image",
                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")]
            )
            if file_path:
                background_var.set(os.path.basename(file_path))
        
        ttk.Button(background_frame, text="...", width=3, command=browse_background).pack(side=tk.LEFT, padx=2)
        
        # Description
        ttk.Label(dialog, text="Description:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        description_text = tk.Text(dialog, width=30, height=5)
        description_text.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        description_text.insert("1.0", scene_data.get("description", ""))
        
        # Script file
        ttk.Label(dialog, text="Script File:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        script_var = tk.StringVar(value=scene_data.get("script", f"{scene_id}.vn"))
        ttk.Entry(dialog, textvariable=script_var, width=30).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        def save_scene():
            # Update scene data
            self.project_config['scenes'][scene_id] = {
                "name": name_var.get().strip() or scene_id,
                "description": description_text.get("1.0", tk.END).strip(),
                "background": background_var.get().strip(),
                "script": script_var.get().strip() or f"{scene_id}.vn"
            }
            
            # Copy background image if provided
            background = background_var.get().strip()
            if background:
                src_path = os.path.join(os.path.dirname(background_var.get()), background)
                if os.path.exists(src_path):
                    dst_path = os.path.join(self.project_dir, "resources", "backgrounds", background)
                    shutil.copy(src_path, dst_path)
            
            # Create script file if it doesn't exist
            script_file = script_var.get().strip() or f"{scene_id}.vn"
            script_path = os.path.join(self.project_dir, "scripts", script_file)
            
            if not os.path.exists(script_path):
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Scene: {scene_id}\n\n@scene:{scene_id}\n\n")
            
            # Save project
            self._save_project()
            
            # Refresh scenes
            self._refresh_scenes()
            
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_scene).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _remove_scene(self):
        """Remove a scene from the project"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
            
        # Get selected scene
        selected_item = self.scenes_tree.focus()
        if not selected_item:
            messagebox.showinfo("Remove Scene", "Please select a scene to remove")
            return
            
        scene_id = self.scenes_tree.item(selected_item, "text")
        
        # Confirm deletion
        if not messagebox.askyesno("Remove Scene", 
                                   f"Are you sure you want to remove the scene '{scene_id}'?\n"
                                   "This will remove it from the project config, but not delete any files."):
            return
        
        try:
            # Remove from project config
            if 'scenes' in self.project_config and scene_id in self.project_config['scenes']:
                del self.project_config['scenes'][scene_id]
            
            # Save project config
            self._save_project()
            
            # Refresh scenes
            self._refresh_scenes()
            
            messagebox.showinfo("Remove Scene", f"Scene '{scene_id}' removed successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove scene: {str(e)}")
    
    def _refresh_scenes(self):
        """Refresh the scenes list"""
        # Clear the treeview
        for item in self.scenes_tree.get_children():
            self.scenes_tree.delete(item)
        
        if not self.project_dir:
            return
        
        # Add scenes from project config
        if 'scenes' in self.project_config:
            for scene_id, scene_data in self.project_config['scenes'].items():
                script_file = scene_data.get("script", f"{scene_id}.vn")
                self.scenes_tree.insert("", "end", text=scene_id, values=(script_file,))
    
    def _add_resource(self):
        """Add a new resource to the project"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Resource")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Resource info
        ttk.Label(dialog, text="Resource Type:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        resource_types = ["Background", "Music", "Sound Effect"]
        type_var = tk.StringVar(value=resource_types[0])
        ttk.Combobox(dialog, textvariable=type_var, values=resource_types, state="readonly").grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="Resource ID:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        id_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=id_var, width=30).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="File:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        file_frame = ttk.Frame(dialog)
        file_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        file_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=file_var, width=20)
        file_entry.pack(side=tk.LEFT)
        
        def browse_file():
            if type_var.get() == "Background":
                file_path = filedialog.askopenfilename(
                    title="Select Background Image",
                    filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")]
                )
            else:
                file_path = filedialog.askopenfilename(
                    title="Select Audio File",
                    filetypes=[("Audio Files", "*.ogg;*.mp3;*.wav"), ("All Files", "*.*")]
                )
                
            if file_path:
                file_var.set(file_path)
        
        ttk.Button(file_frame, text="...", width=3, command=browse_file).pack(side=tk.LEFT, padx=2)
        
        # Description
        ttk.Label(dialog, text="Description:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        description_text = tk.Text(dialog, width=30, height=3)
        description_text.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        def save_resource():
            resource_id = id_var.get().strip()
            if not resource_id:
                messagebox.showwarning("Warning", "Resource ID is required")
                return
                
            file_path = file_var.get().strip()
            if not file_path or not os.path.exists(file_path):
                messagebox.showwarning("Warning", "Please select a valid file")
                return
                
            try:
                # Determine resource type and destination
                resource_type = type_var.get()
                
                if resource_type == "Background":
                    resource_dir = os.path.join(self.project_dir, "resources", "backgrounds")
                    config_key = "backgrounds"
                elif resource_type == "Music":
                    resource_dir = os.path.join(self.project_dir, "resources", "music")
                    config_key = "music"
                else:  # Sound Effect
                    resource_dir = os.path.join(self.project_dir, "resources", "sound")
                    config_key = "sound"
                
                # Create directory if it doesn't exist
                os.makedirs(resource_dir, exist_ok=True)
                
                # Copy file
                file_name = os.path.basename(file_path)
                dst_path = os.path.join(resource_dir, file_name)
                shutil.copy(file_path, dst_path)
                
                # Update project config
                if 'resources' not in self.project_config:
                    self.project_config['resources'] = {}
                    
                if config_key not in self.project_config['resources']:
                    self.project_config['resources'][config_key] = {}
                    
                self.project_config['resources'][config_key][resource_id] = {
                    "file": os.path.join("resources", 
                                         "backgrounds" if config_key == "backgrounds" else 
                                         "music" if config_key == "music" else "sound", 
                                         file_name),
                    "description": description_text.get("1.0", tk.END).strip()
                }
                
                # Save project
                self._save_project()
                
                # Refresh resources
                self._refresh_resources()
                
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add resource: {str(e)}")
        
        ttk.Button(button_frame, text="Save", command=save_resource).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _import_resources(self):
        """Import multiple resources at once"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Resources")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("600x400")
        
        # Resource type selection
        ttk.Label(dialog, text="Resource Type:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        resource_types = ["Backgrounds", "Music", "Sound Effects"]
        type_var = tk.StringVar(value=resource_types[0])
        ttk.Combobox(dialog, textvariable=type_var, values=resource_types, state="readonly").grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Directory selection
        ttk.Label(dialog, text="Source Directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        dir_frame = ttk.Frame(dialog)
        dir_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=dir_var, width=40)
        dir_entry.pack(side=tk.LEFT)
        
        def browse_dir():
            dir_path = filedialog.askdirectory(title="Select Source Directory")
            if dir_path:
                dir_var.set(dir_path)
                # Populate file list
                refresh_file_list()
        
        ttk.Button(dir_frame, text="...", width=3, command=browse_dir).pack(side=tk.LEFT, padx=2)
        
        # Files list
        ttk.Label(dialog, text="Files to Import:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        files_frame = ttk.Frame(dialog)
        files_frame.grid(row=2, column=1, sticky=tk.NSEW, padx=5, pady=5)
        dialog.grid_rowconfigure(2, weight=1)
        dialog.grid_columnconfigure(1, weight=1)
        
        # Create a list with checkbuttons
        files_list = tk.Listbox(files_frame, selectmode=tk.MULTIPLE)
        files_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=files_list.yview)
        files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        files_list.config(yscrollcommand=files_scrollbar.set)
        
        # Function to refresh file list
        def refresh_file_list():
            files_list.delete(0, tk.END)
            
            dir_path = dir_var.get()
            if not dir_path or not os.path.isdir(dir_path):
                return
                
            # Filter files by type
            if type_var.get() == "Backgrounds":
                extensions = (".png", ".jpg", ".jpeg", ".bmp")
            else:  # Music or Sound Effects
                extensions = (".ogg", ".mp3", ".wav")
                
            for item in os.listdir(dir_path):
                if item.lower().endswith(extensions):
                    files_list.insert(tk.END, item)
        
        # Update file list when type changes
        type_var.trace_add("write", lambda *args: refresh_file_list())
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        def import_resources():
            selected_indices = files_list.curselection()
            if not selected_indices:
                messagebox.showwarning("Warning", "No files selected for import")
                return
                
            dir_path = dir_var.get()
            if not dir_path or not os.path.isdir(dir_path):
                messagebox.showwarning("Warning", "Please select a valid source directory")
                return
                
            try:
                resource_type = type_var.get()
                
                if resource_type == "Backgrounds":
                    resource_dir = os.path.join(self.project_dir, "resources", "backgrounds")
                    config_key = "backgrounds"
                elif resource_type == "Music":
                    resource_dir = os.path.join(self.project_dir, "resources", "music")
                    config_key = "music"
                else:  # Sound Effects
                    resource_dir = os.path.join(self.project_dir, "resources", "sound")
                    config_key = "sound"
                
                # Create directory if it doesn't exist
                os.makedirs(resource_dir, exist_ok=True)
                
                # Ensure resources section exists in config
                if 'resources' not in self.project_config:
                    self.project_config['resources'] = {}
                    
                if config_key not in self.project_config['resources']:
                    self.project_config['resources'][config_key] = {}
                
                # Copy each selected file
                import_count = 0
                for index in selected_indices:
                    file_name = files_list.get(index)
                    src_path = os.path.join(dir_path, file_name)
                    dst_path = os.path.join(resource_dir, file_name)
                    
                    # Copy file
                    shutil.copy(src_path, dst_path)
                    
                    # Generate resource ID from filename
                    resource_id = os.path.splitext(file_name)[0]
                    
                    # Add to project config
                    self.project_config['resources'][config_key][resource_id] = {
                        "file": os.path.join("resources", 
                                            "backgrounds" if config_key == "backgrounds" else 
                                            "music" if config_key == "music" else "sound", 
                                            file_name),
                        "description": ""
                    }
                    
                    import_count += 1
                
                # Save project
                self._save_project()
                
                # Refresh resources
                self._refresh_resources()
                
                messagebox.showinfo("Import Resources", f"Successfully imported {import_count} resources")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import resources: {str(e)}")
        
        ttk.Button(button_frame, text="Import Selected", command=import_resources).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _refresh_resources(self):
        """Refresh the resources tree"""
        # Clear the treeview
        for item in self.resources_tree.get_children():
            self.resources_tree.delete(item)
        
        if not self.project_dir:
            return
        
        # Add initial resource categories
        categories = {
            "Backgrounds": "",
            "Characters": "",
            "Music": "",
            "Sound Effects": ""
        }
        
        for category in categories:
            categories[category] = self.resources_tree.insert("", "end", text=category, open=True)
        
        # Add resources from project config
        if 'resources' in self.project_config:
            # Backgrounds
            if 'backgrounds' in self.project_config['resources']:
                for bg_id, bg_data in self.project_config['resources']['backgrounds'].items():
                    self.resources_tree.insert(categories["Backgrounds"], "end", text=bg_id)
            
            # Characters
            if 'characters' in self.project_config['resources']:
                for char_id, char_data in self.project_config['resources']['characters'].items():
                    self.resources_tree.insert(categories["Characters"], "end", text=char_id)
            
            # Music
            if 'music' in self.project_config['resources']:
                for music_id, music_data in self.project_config['resources']['music'].items():
                    self.resources_tree.insert(categories["Music"], "end", text=music_id)
            
            # Sound Effects
            if 'sound' in self.project_config['resources']:
                for sound_id, sound_data in self.project_config['resources']['sound'].items():
                    self.resources_tree.insert(categories["Sound Effects"], "end", text=sound_id)
    
    def _analyze_script_structure(self):
        """Analyze the script structure and show it in the structure tab"""
        editor = self._get_current_editor()
        if not editor:
            messagebox.showinfo("Analysis", "Please open a script file first")
            return
        
        # Get the script content
        script_content = editor.get("1.0", tk.END)
        
        # Clear the structure tree
        for item in self.structure_tree.get_children():
            self.structure_tree.delete(item)
        
        # Analyze structure
        try:
            # Add root for the current script
            current_tab = self.editor_notebook.select()
            tab_text = self.editor_notebook.tab(current_tab, "text")
            root_node = self.structure_tree.insert("", "end", text=tab_text, open=True)
            
            # Track current section
            current_section = None
            
            # Parse lines
            lines = script_content.split("\n")
            for i, line in enumerate(lines):
                line_num = i + 1
                
                # Look for sections
                if line.startswith("#") and not line.startswith("##"):
                    # Main section
                    section_text = line.lstrip("# ").strip()
                    current_section = self.structure_tree.insert(root_node, "end", text=section_text, 
                                                              values=(f"Line {line_num}",))
                
                # Look for scenes
                elif line.startswith("@scene:"):
                    scene_match = re.match(r"@scene:([^:]+)(?::(.+))?", line)
                    if scene_match:
                        scene_id = scene_match.group(1).strip()
                        transition = scene_match.group(2).strip() if scene_match.group(2) else ""
                        
                        scene_text = f"Scene: {scene_id}" + (f" ({transition})" if transition else "")
                        
                        if current_section:
                            self.structure_tree.insert(current_section, "end", text=scene_text, 
                                                     values=(f"Line {line_num}",))
                        else:
                            self.structure_tree.insert(root_node, "end", text=scene_text, 
                                                     values=(f"Line {line_num}",))
                
                # Look for characters
                elif line.startswith("@character:"):
                    char_match = re.match(r"@character:([^:]+)", line)
                    if char_match:
                        char_id = char_match.group(1).strip()
                        
                        # Get dialogue text (next line)
                        dialogue = ""
                        if i + 1 < len(lines):
                            dialogue = lines[i + 1].strip()
                            if len(dialogue) > 30:
                                dialogue = dialogue[:27] + "..."
                        
                        char_text = f"{char_id}: {dialogue}" if dialogue else char_id
                        
                        if current_section:
                            self.structure_tree.insert(current_section, "end", text=char_text, 
                                                     values=(f"Line {line_num}",))
                        else:
                            self.structure_tree.insert(root_node, "end", text=char_text, 
                                                     values=(f"Line {line_num}",))
                
                # Look for choices
                elif line.startswith("->"):
                    choice_text = line[2:].strip()
                    
                    if current_section:
                        self.structure_tree.insert(current_section, "end", text=f"Choice: {choice_text}", 
                                                 values=(f"Line {line_num}",))
                    else:
                        self.structure_tree.insert(root_node, "end", text=f"Choice: {choice_text}", 
                                                 values=(f"Line {line_num}",))
            
            self.status_bar.config(text="Script structure analyzed successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze script structure: {str(e)}")
    
    def _navigate_to_scene(self):
        """Navigate to a specific scene in the script"""
        editor = self._get_current_editor()
        if not editor:
            messagebox.showinfo("Navigation", "Please open a script file first")
            return
        
        # Get available scenes
        scenes = self._get_available_scenes_in_script(editor.get("1.0", tk.END))
        
        if not scenes:
            messagebox.showinfo("Navigation", "No scenes found in the current script")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Navigate to Scene")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select Scene:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Create a listbox for scenes
        scenes_listbox = tk.Listbox(dialog, width=40, height=10)
        scenes_listbox.grid(row=1, column=0, padx=5, pady=5)
        
        # Add scenes to listbox
        for scene_id, line_num in scenes:
            scenes_listbox.insert(tk.END, f"{scene_id} (Line {line_num})")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, pady=10)
        
        def navigate():
            selection = scenes_listbox.curselection()
            if selection:
                index = selection[0]
                scene_id, line_num = scenes[index]
                
                # Navigate to the line
                editor.see(f"{line_num}.0")
                editor.mark_set(tk.INSERT, f"{line_num}.0")
                editor.tag_remove(tk.SEL, "1.0", tk.END)
                editor.tag_add(tk.SEL, f"{line_num}.0", f"{line_num}.0 lineend")
                editor.focus_set()
                
                dialog.destroy()
        
        ttk.Button(button_frame, text="Go to Scene", command=navigate).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Double-click to navigate
        scenes_listbox.bind("<Double-1>", lambda e: navigate())
    
    def _get_available_scenes_in_script(self, script_content):
        """Get a list of scenes in the script content"""
        scenes = []
        
        lines = script_content.split("\n")
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Look for scenes
            if line.startswith("@scene:"):
                scene_match = re.match(r"@scene:([^:]+)(?::(.+))?", line)
                if scene_match:
                    scene_id = scene_match.group(1).strip()
                    scenes.append((scene_id, line_num))
        
        return scenes
    
    def _navigate_to_element(self, event):
        """Navigate to the selected element in the structure tree"""
        editor = self._get_current_editor()
        if not editor:
            return
            
        selected_item = self.structure_tree.focus()
        if not selected_item:
            return
            
        values = self.structure_tree.item(selected_item, "values")
        if not values:
            return
            
        line_info = values[0]
        if line_info.startswith("Line "):
            try:
                line_num = int(line_info[5:])
                
                # Navigate to the line
                editor.see(f"{line_num}.0")
                editor.mark_set(tk.INSERT, f"{line_num}.0")
                editor.tag_remove(tk.SEL, "1.0", tk.END)
                editor.tag_add(tk.SEL, f"{line_num}.0", f"{line_num}.0 lineend")
                editor.focus_set()
            except ValueError:
                pass
    
    def _check_script_flow(self):
        """Check for issues in the script flow"""
        editor = self._get_current_editor()
        if not editor:
            messagebox.showinfo("Script Check", "Please open a script file first")
            return
        
        # Get the script content
        script_content = editor.get("1.0", tk.END)
        
        # Create a dialog to show results
        dialog = tk.Toplevel(self.root)
        dialog.title("Script Flow Check")
        dialog.transient(self.root)
        dialog.geometry("600x400")
        
        # Results text
        results_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=70, height=20)
        results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def add_result(text, is_error=False):
            """Add a result line with optional error formatting"""
            if is_error:
                results_text.insert(tk.END, text + "\n", "error")
            else:
                results_text.insert(tk.END, text + "\n")
        
        results_text.tag_configure("error", foreground="red")
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
        
        # Check script flow
        try:
            add_result("Checking script flow...")
            add_result("--------------------")
            
            # Check for scene declarations
            scenes = []
            scene_pattern = r"@scene:([^:]+)(?::(.+))?"
            scene_matches = re.finditer(scene_pattern, script_content)
            
            for match in scene_matches:
                scene_id = match.group(1).strip()
                scenes.append(scene_id)
            
            if not scenes:
                add_result("No scenes found in the script!", True)
            else:
                add_result(f"Found {len(scenes)} scenes: {', '.join(scenes)}")
            
            # Check for character declarations
            characters = set()
            char_pattern = r"@character:([^:]+)"
            char_matches = re.finditer(char_pattern, script_content)
            
            for match in char_matches:
                char_id = match.group(1).strip()
                characters.add(char_id)
            
            if not characters:
                add_result("No characters found in the script!", True)
            else:
                add_result(f"Found {len(characters)} characters: {', '.join(characters)}")
            
            # Check for choices
            choices = []
            lines = script_content.split("\n")
            choice_count = 0
            
            for i, line in enumerate(lines):
                if line.startswith("->"):
                    choice_text = line[2:].strip()
                    choice_count += 1
                    
                    # Check if this choice is followed by another
                    if i + 1 < len(lines) and lines[i + 1].startswith("->"):
                        continue
                    
                    # This is the last choice in a group
                    choices.append(choice_count)
                    choice_count = 0
            
            if not choices:
                add_result("No choices found in the script!", True)
            else:
                add_result(f"Found {sum(choices)} choices in {len(choices)} choice groups")
                for i, count in enumerate(choices):
                    add_result(f"  Choice group {i+1}: {count} options")
            
            # Check for missing character expressions
            char_expr_pattern = r"@([^:]+):([^:]+)"
            char_expr_matches = re.finditer(char_expr_pattern, script_content)
            
            undefined_chars = set()
            
            for match in char_expr_matches:
                char_id = match.group(1).strip()
                if char_id not in ["scene", "character", "bgm", "sound"] and char_id not in characters:
                    undefined_chars.add(char_id)
            
            if undefined_chars:
                add_result("Found references to undefined characters:", True)
                for char in undefined_chars:
                    add_result(f"  - {char}", True)
            
            # Check for orphaned dialogue (not preceded by a character declaration)
            in_dialogue = False
            dialogue_count = 0
            orphaned_dialogue = 0
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Check for character or expression declarations
                if (line.startswith("@character:") or 
                    re.match(r"@[^:]+:[^:]+", line) and not line.startswith("@scene:") and 
                    not line.startswith("@bgm:") and not line.startswith("@sound:")):
                    in_dialogue = True
                    dialogue_count += 1
                elif line.startswith("@") or line.startswith("->"):
                    in_dialogue = False
                # If it's not a command and not in dialogue, it might be orphaned
                elif not in_dialogue and line and not line.startswith("@") and not line.startswith("->"):
                    orphaned_dialogue += 1
            
            if orphaned_dialogue > 0:
                add_result(f"Found {orphaned_dialogue} lines of dialogue without character attribution!", True)
                add_result("  These lines may not display correctly in-game.", True)
            
            add_result("--------------------")
            add_result("Script check complete!")
            
        except Exception as e:
            add_result(f"Error checking script: {str(e)}", True)
    
    def _validate_script(self):
        """Validate the current script for syntax errors"""
        editor = self._get_current_editor()
        if not editor:
            messagebox.showinfo("Validation", "Please open a script file first")
            return
        
        # Get the script content
        script_content = editor.get("1.0", tk.END)
        
        # Create a dialog to show results
        dialog = tk.Toplevel(self.root)
        dialog.title("Script Validation")
        dialog.transient(self.root)
        dialog.geometry("600x400")
        
        # Results text
        results_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=70, height=20)
        results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def add_result(text, is_error=False):
            """Add a result line with optional error formatting"""
            if is_error:
                results_text.insert(tk.END, text + "\n", "error")
            else:
                results_text.insert(tk.END, text + "\n")
        
        results_text.tag_configure("error", foreground="red")
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
        
        # Validate script
        errors = 0
        warnings = 0
        
        try:
            lines = script_content.split("\n")
            
            add_result("Validating script...")
            add_result("--------------------")
            
            # Check for valid commands
            for i, line in enumerate(lines):
                line_num = i + 1
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Check commands
                if line.startswith("@"):
                    # Scene command
                    if line.startswith("@scene:"):
                        if not re.match(r"@scene:[^:]+(?::[^:]+)?$", line):
                            add_result(f"Line {line_num}: Invalid scene command format: {line}", True)
                            errors += 1
                    
                    # Character command
                    elif line.startswith("@character:"):
                        if not re.match(r"@character:[^:]+$", line):
                            add_result(f"Line {line_num}: Invalid character command format: {line}", True)
                            errors += 1
                    
                    # Character expression
                    elif re.match(r"@[^:]+:[^:]+$", line):
                        pass  # Valid format
                    
                    # BGM command
                    elif line.startswith("@bgm:"):
                        if not re.match(r"@bgm:[^:]+(?::[^:]+)?(?::[^:]+)?$", line):
                            add_result(f"Line {line_num}: Invalid BGM command format: {line}", True)
                            errors += 1
                    
                    # Sound command
                    elif line.startswith("@sound:"):
                        if not re.match(r"@sound:[^:]+(?::[^:]+)?$", line):
                            add_result(f"Line {line_num}: Invalid sound command format: {line}", True)
                            errors += 1
                    
                    # Unknown command
                    else:
                        add_result(f"Line {line_num}: Unknown command: {line}", True)
                        errors += 1
                
                # Check choices
                elif line.startswith("->"):
                    if not line[2:].strip():
                        add_result(f"Line {line_num}: Empty choice text: {line}", True)
                        errors += 1
            
            # Check for unclosed formatting tags
            bold_count = script_content.count("**")
            if bold_count % 2 != 0:
                add_result("Warning: Unclosed bold formatting tags (**)", True)
                warnings += 1
                
            italic_count = 0
            in_bold = False
            for c in script_content:
                if c == "*":
                    if not in_bold:
                        italic_count += 1
                if c == "*" and script_content.find("**", script_content.index(c)) == script_content.index(c):
                    in_bold = not in_bold
            
            if italic_count % 2 != 0:
                add_result("Warning: Unclosed italic formatting tags (*)", True)
                warnings += 1
            
            add_result("--------------------")
            
            if errors == 0 and warnings == 0:
                add_result("Script validation passed! No errors or warnings found.")
            else:
                add_result(f"Script validation finished with {errors} errors and {warnings} warnings.", True)
            
        except Exception as e:
            add_result(f"Error validating script: {str(e)}", True)
    
    def _generate_preview(self):
        """Generate a preview of the script"""
        editor = self._get_current_editor()
        if not editor:
            messagebox.showinfo("Preview", "Please open a script file first")
            return
        
        # Get the script content
        script_content = editor.get("1.0", tk.END)
        
        # Clear preview text
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        
        # Process script for preview
        try:
            lines = script_content.split("\n")
            current_scene = None
            current_character = None
            
            # Configure tags for preview
            self.preview_text.tag_configure("heading", font=("Arial", 14, "bold"))
            self.preview_text.tag_configure("scene", font=("Arial", 12, "bold"), foreground="blue")
            self.preview_text.tag_configure("character", font=("Arial", 11, "bold"), foreground="red")
            self.preview_text.tag_configure("dialogue", font=("Arial", 11))
            self.preview_text.tag_configure("choice", font=("Arial", 11, "italic"), foreground="green")
            self.preview_text.tag_configure("bold", font=("Arial", 11, "bold"))
            self.preview_text.tag_configure("italic", font=("Arial", 11, "italic"))
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                i += 1
                
                # Skip empty lines
                if not line:
                    continue
                
                # Process comments as headings
                if line.startswith("#") and not line.startswith("##"):
                    heading_text = line.lstrip("# ").strip()
                    self.preview_text.insert(tk.END, f"{heading_text}\n\n", "heading")
                    continue
                
                # Process scene declarations
                if line.startswith("@scene:"):
                    scene_match = re.match(r"@scene:([^:]+)(?::(.+))?", line)
                    if scene_match:
                        current_scene = scene_match.group(1).strip()
                        transition = scene_match.group(2) if scene_match.group(2) else "fade"
                        
                        self.preview_text.insert(tk.END, f"[Scene: {current_scene} ({transition})]\n\n", "scene")
                    continue
                
                # Process character declarations
                if line.startswith("@character:"):
                    char_match = re.match(r"@character:([^:]+)", line)
                    if char_match:
                        current_character = char_match.group(1).strip()
                        
                        # Get the next line as dialogue
                        if i < len(lines):
                            dialogue = lines[i].strip()
                            i += 1
                            
                            # Format character and dialogue
                            self.preview_text.insert(tk.END, f"{current_character}: ", "character")
                            
                            # Process any formatting in the dialogue
                            self._insert_formatted_text(dialogue)
                            self.preview_text.insert(tk.END, "\n\n")
                    continue
                
                # Process character expressions
                char_expr_match = re.match(r"@([^:]+):([^:]+)", line)
                if char_expr_match and not line.startswith("@scene:") and not line.startswith("@bgm:") and not line.startswith("@sound:"):
                    char_id = char_expr_match.group(1).strip()
                    expression = char_expr_match.group(2).strip()
                    current_character = char_id
                    
                    # Get the next line as dialogue
                    if i < len(lines):
                        dialogue = lines[i].strip()
                        i += 1
                        
                        # Format character and dialogue
                        self.preview_text.insert(tk.END, f"{current_character} [{expression}]: ", "character")
                        
                        # Process any formatting in the dialogue
                        self._insert_formatted_text(dialogue)
                        self.preview_text.insert(tk.END, "\n\n")
                    continue
                
                # Process choices
                if line.startswith("->"):
                    choice_text = line[2:].strip()
                    self.preview_text.insert(tk.END, f"• {choice_text}\n", "choice")
                    
                    # Check if there are more choices
                    while i < len(lines) and lines[i].startswith("->"):
                        choice_text = lines[i][2:].strip()
                        self.preview_text.insert(tk.END, f"• {choice_text}\n", "choice")
                        i += 1
                    
                    self.preview_text.insert(tk.END, "\n")
                    continue
                
                # Process BGM
                if line.startswith("@bgm:"):
                    bgm_match = re.match(r"@bgm:([^:]+)(?::(.+))?", line)
                    if bgm_match:
                        bgm_id = bgm_match.group(1).strip()
                        self.preview_text.insert(tk.END, f"[BGM: {bgm_id}]\n\n", "italic")
                    continue
                
                # Process sound effects
                if line.startswith("@sound:"):
                    sound_match = re.match(r"@sound:([^:]+)(?::(.+))?", line)
                    if sound_match:
                        sound_id = sound_match.group(1).strip()
                        self.preview_text.insert(tk.END, f"[Sound: {sound_id}]\n\n", "italic")
                    continue
                
                # Any other text (probably dialogue without character tag)
                if line and not line.startswith("#"):
                    self._insert_formatted_text(line)
                    self.preview_text.insert(tk.END, "\n\n")
            
            # Switch to the preview tab
            self.right_notebook.select(self.preview_frame)
            
        except Exception as e:
            self.preview_text.insert(tk.END, f"Error generating preview: {str(e)}", "bold")
        
        # Disable editing of preview
        self.preview_text.config(state=tk.DISABLED)
    
    def _insert_formatted_text(self, text):
        """Insert text with formatting (bold, italic) into the preview"""
        # Process bold formatting
        bold_fragments = text.split("**")
        if len(bold_fragments) > 1:
            for i, fragment in enumerate(bold_fragments):
                # Check for italic formatting within this fragment
                if i % 2 == 1:
                    # This is a bold section
                    self._insert_italic_formatted_text(fragment, "bold")
                else:
                    # This is a regular section
                    self._insert_italic_formatted_text(fragment, "dialogue")
        else:
            # No bold formatting, just check for italic
            self._insert_italic_formatted_text(text, "dialogue")
    
    def _insert_italic_formatted_text(self, text, base_tag):
        """Insert text with italic formatting into the preview"""
        italic_fragments = text.split("*")
        if len(italic_fragments) > 1:
            for i, fragment in enumerate(italic_fragments):
                if i % 2 == 1 and fragment:
                    # This is an italic section
                    if base_tag == "bold":
                        self.preview_text.insert(tk.END, fragment, "bold")
                    else:
                        self.preview_text.insert(tk.END, fragment, "italic")
                else:
                    # This is a regular section
                    self.preview_text.insert(tk.END, fragment, base_tag)
        else:
            # No italic formatting
            self.preview_text.insert(tk.END, text, base_tag)
    
    def _compile_script(self):
        """Compile the script into a format suitable for the VN engine"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Create a dialog to show compilation progress
        dialog = tk.Toplevel(self.root)
        dialog.title("Compile Script")
        dialog.transient(self.root)
        dialog.geometry("500x300")
        
        # Progress text
        progress_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=60, height=15)
        progress_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def add_progress(text):
            """Add a line to the progress text"""
            progress_text.insert(tk.END, text + "\n")
            progress_text.see(tk.END)
            dialog.update()
        
        progress_text.insert(tk.END, "Compiling script...\n")
        progress_text.insert(tk.END, "--------------------\n")
        
        try:
            # Get all script files
            script_dir = os.path.join(self.project_dir, "scripts")
            if not os.path.exists(script_dir):
                add_progress("Error: Script directory not found!")
                return
                
            script_files = [f for f in os.listdir(script_dir) if f.endswith(".vn")]
            if not script_files:
                add_progress("Error: No script files found!")
                return
                
            add_progress(f"Found {len(script_files)} script files")
            
            # Create output directory
            output_dir = os.path.join(self.project_dir, "build")
            os.makedirs(output_dir, exist_ok=True)
            
            # Compile script files into JSON
            compiled_script = {
                "title": self.project_config.get("name", "Visual Novel"),
                "author": self.project_config.get("author", "Unknown"),
                "version": self.project_config.get("version", "0.1"),
                "start": self.project_config.get("start_scene", "main"),
                "nodes": {},
                "variables": {}
            }
            
            # Process each script file
            for script_file in script_files:
                add_progress(f"Processing {script_file}...")
                script_path = os.path.join(script_dir, script_file)
                
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
                
                # Parse the script
                self._parse_script_file(script_content, compiled_script, add_progress)
            
            # Save compiled script
            output_path = os.path.join(output_dir, "script.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(compiled_script, f, indent=2)
            
            add_progress(f"Script compiled successfully to {output_path}")
            add_progress("--------------------")
            add_progress("Compilation complete!")
            
            # Close button
            ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
            
        except Exception as e:
            add_progress(f"Error compiling script: {str(e)}")
            # Close button
            ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def _parse_script_file(self, script_content, compiled_script, log_function):
        """Parse a script file and add its nodes to the compiled script"""
        lines = script_content.split("\n")
        
        current_node_id = None
        current_node = None
        node_counter = len(compiled_script["nodes"])
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            # Scene declaration creates a new node
            if line.startswith("@scene:"):
                scene_match = re.match(r"@scene:([^:]+)(?::(.+))?", line)
                if scene_match:
                    scene_id = scene_match.group(1).strip()
                    transition = scene_match.group(2).strip() if scene_match.group(2) else "fade"
                    
                    # Create a new node
                    current_node_id = f"scene_{scene_id}_{node_counter}"
                    node_counter += 1
                    
                    current_node = {
                        "type": "dialogue",
                        "scene": scene_id,
                        "transition": transition,
                        "characters": {},
                        "text": ""
                    }
                    
                    compiled_script["nodes"][current_node_id] = current_node
                    
                    log_function(f"Created scene node: {current_node_id}")
            
            # Character dialogue
            elif line.startswith("@character:"):
                char_match = re.match(r"@character:([^:]+)", line)
                if char_match:
                    char_id = char_match.group(1).strip()
                    
                    # Get the dialogue text
                    dialogue = ""
                    if i < len(lines):
                        dialogue = lines[i].strip()
                        i += 1
                    
                    # If we don't have a current node, create one
                    if not current_node:
                        current_node_id = f"dialogue_{node_counter}"
                        node_counter += 1
                        
                        current_node = {
                            "type": "dialogue",
                            "characters": {},
                            "text": ""
                        }
                        
                        compiled_script["nodes"][current_node_id] = current_node
                    
                    # Update current node
                    if "character" not in current_node:
                        current_node["character"] = char_id
                    
                    current_node["characters"][char_id] = {
                        "position": "center",
                        "expression": "neutral",
                        "visible": True
                    }
                    
                    current_node["text"] = dialogue
            
            # Character expression
            elif re.match(r"@([^:]+):([^:]+)", line) and not line.startswith("@scene:") and not line.startswith("@bgm:") and not line.startswith("@sound:"):
                char_expr_match = re.match(r"@([^:]+):([^:]+)", line)
                if char_expr_match:
                    char_id = char_expr_match.group(1).strip()
                    expression = char_expr_match.group(2).strip()
                    
                    # Get the dialogue text
                    dialogue = ""
                    if i < len(lines):
                        dialogue = lines[i].strip()
                        i += 1
                    
                    # If we don't have a current node, create one
                    if not current_node:
                        current_node_id = f"dialogue_{node_counter}"
                        node_counter += 1
                        
                        current_node = {
                            "type": "dialogue",
                            "characters": {},
                            "text": ""
                        }
                        
                        compiled_script["nodes"][current_node_id] = current_node
                    
                    # Update current node
                    if "character" not in current_node:
                        current_node["character"] = char_id
                    
                    current_node["characters"][char_id] = {
                        "position": "center",
                        "expression": expression,
                        "visible": True
                    }
                    
                    current_node["text"] = dialogue
            
            # Choice declaration creates a new choice node
            elif line.startswith("->"):
                choices = []
                
                # First choice
                choice_text = line[2:].strip()
                choices.append(choice_text)
                
                # Collect all choices
                while i < len(lines) and lines[i].startswith("->"):
                    choice_text = lines[i][2:].strip()
                    choices.append(choice_text)
                    i += 1
                
                # Create a choice node
                current_node_id = f"choice_{node_counter}"
                node_counter += 1
                
                current_node = {
                    "type": "choice",
                    "text": "",
                    "choices": []
                }
                
                # Add choice targets (just basic targets for now)
                for j, choice in enumerate(choices):
                    target_node_id = f"choice_target_{node_counter}_{j}"
                    node_counter += 1
                    
                    # Create target node (empty for now)
                    compiled_script["nodes"][target_node_id] = {
                        "type": "dialogue",
                        "text": ""
                    }
                    
                    # Add choice to current node
                    current_node["choices"].append({
                        "text": choice,
                        "target": target_node_id
                    })
                
                compiled_script["nodes"][current_node_id] = current_node
                log_function(f"Created choice node: {current_node_id} with {len(choices)} choices")
            
            # BGM declaration
            elif line.startswith("@bgm:"):
                bgm_match = re.match(r"@bgm:([^:]+)(?::(.+))?", line)
                if bgm_match:
                    bgm_id = bgm_match.group(1).strip()
                    fade_in = bgm_match.group(2).strip() if bgm_match.group(2) else "0"
                    
                    # If we don't have a current node, create one
                    if not current_node:
                        current_node_id = f"bgm_{node_counter}"
                        node_counter += 1
                        
                        current_node = {
                            "type": "dialogue",
                            "text": ""
                        }
                        
                        compiled_script["nodes"][current_node_id] = current_node
                    
                    # Update current node
                    current_node["bgm"] = bgm_id
                    try:
                        current_node["bgm_fade_in"] = float(fade_in)
                    except ValueError:
                        current_node["bgm_fade_in"] = 0
            
            # Sound effect declaration
            elif line.startswith("@sound:"):
                sound_match = re.match(r"@sound:([^:]+)(?::(.+))?", line)
                if sound_match:
                    sound_id = sound_match.group(1).strip()
                    volume = sound_match.group(2).strip() if sound_match.group(2) else "100"
                    
                    # If we don't have a current node, create one
                    if not current_node:
                        current_node_id = f"sound_{node_counter}"
                        node_counter += 1
                        
                        current_node = {
                            "type": "dialogue",
                            "text": ""
                        }
                        
                        compiled_script["nodes"][current_node_id] = current_node
                    
                    # Update current node
                    current_node["sound"] = sound_id
                    try:
                        current_node["sound_volume"] = int(volume)
                    except ValueError:
                        current_node["sound_volume"] = 100
        
        # Link nodes in sequence if not already linked
        node_ids = list(compiled_script["nodes"].keys())
        for j in range(len(node_ids) - 1):
            current = compiled_script["nodes"][node_ids[j]]
            
            # If it's a dialogue node and doesn't have a next property
            if current.get("type") == "dialogue" and "next" not in current:
                # Skip choice nodes as targets are already defined
                next_idx = j + 1
                while next_idx < len(node_ids) and compiled_script["nodes"][node_ids[next_idx]].get("type") == "choice":
                    next_idx += 1
                
                if next_idx < len(node_ids):
                    current["next"] = node_ids[next_idx]
    
    def _export_script(self):
        """Export the script to a different format"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Export Script")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Export options
        ttk.Label(dialog, text="Export Format:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        format_var = tk.StringVar(value="Text")
        format_options = ["Text", "HTML", "Markdown", "Game Script"]
        ttk.Combobox(dialog, textvariable=format_var, values=format_options, state="readonly").grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Output options
        ttk.Label(dialog, text="Export Options:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        options_frame = ttk.Frame(dialog)
        options_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        include_comments_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include comments", variable=include_comments_var).pack(anchor=tk.W)
        
        include_commands_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Include commands", variable=include_commands_var).pack(anchor=tk.W)
        
        # Output file
        ttk.Label(dialog, text="Output File:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        file_frame = ttk.Frame(dialog)
        file_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        file_var = tk.StringVar(value=os.path.join(self.project_dir, "export", "script.txt"))
        file_entry = ttk.Entry(file_frame, textvariable=file_var, width=40)
        file_entry.pack(side=tk.LEFT)
        
        def browse_file():
            # Determine file extension based on format
            format_type = format_var.get()
            if format_type == "Text":
                ext = ".txt"
            elif format_type == "HTML":
                ext = ".html"
            elif format_type == "Markdown":
                ext = ".md"
            else:
                ext = ".json"
                
            file_path = filedialog.asksaveasfilename(
                title="Export Script",
                initialdir=os.path.join(self.project_dir, "export"),
                initialfile=f"script{ext}",
                defaultextension=ext,
                filetypes=[
                    ("Text Files", "*.txt"),
                    ("HTML Files", "*.html"),
                    ("Markdown Files", "*.md"),
                    ("JSON Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if file_path:
                file_var.set(file_path)
        
        ttk.Button(file_frame, text="...", width=3, command=browse_file).pack(side=tk.LEFT, padx=2)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        def export_script():
            format_type = format_var.get()
            output_file = file_var.get()
            
            if not output_file:
                messagebox.showwarning("Warning", "Please specify an output file")
                return
                
            try:
                # Create output directory if it doesn't exist
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                # Get all script files
                script_dir = os.path.join(self.project_dir, "scripts")
                if not os.path.exists(script_dir):
                    messagebox.showerror("Error", "Script directory not found!")
                    return
                    
                script_files = [f for f in os.listdir(script_dir) if f.endswith(".vn")]
                if not script_files:
                    messagebox.showerror("Error", "No script files found!")
                    return
                
                # Process script files based on format
                if format_type == "Text":
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"{self.project_config.get('name', 'Visual Novel')}\n")
                        f.write(f"By {self.project_config.get('author', 'Unknown')}\n\n")
                        
                        for script_file in script_files:
                            script_path = os.path.join(script_dir, script_file)
                            f.write(f"---- {script_file} ----\n\n")
                            
                            with open(script_path, 'r', encoding='utf-8') as sf:
                                script_content = sf.read()
                                
                            # Process script content
                            lines = script_content.split("\n")
                            
                            for line in lines:
                                line = line.strip()
                                
                                # Skip empty lines
                                if not line:
                                    f.write("\n")
                                    continue
                                
                                # Include comments if requested
                                if line.startswith("#"):
                                    if include_comments_var.get():
                                        f.write(f"{line}\n")
                                    continue
                                
                                # Process commands
                                if line.startswith("@"):
                                    if line.startswith("@scene:"):
                                        scene_match = re.match(r"@scene:([^:]+)(?::(.+))?", line)
                                        if scene_match:
                                            scene_id = scene_match.group(1).strip()
                                            f.write(f"[Scene: {scene_id}]\n\n")
                                    elif line.startswith("@character:"):
                                        if include_commands_var.get():
                                            f.write(f"{line}\n")
                                    elif line.startswith("@bgm:"):
                                        if include_commands_var.get():
                                            bgm_match = re.match(r"@bgm:([^:]+)(?::(.+))?", line)
                                            if bgm_match:
                                                bgm_id = bgm_match.group(1).strip()
                                                f.write(f"[Music: {bgm_id}]\n")
                                    elif line.startswith("@sound:"):
                                        if include_commands_var.get():
                                            sound_match = re.match(r"@sound:([^:]+)(?::(.+))?", line)
                                            if sound_match:
                                                sound_id = sound_match.group(1).strip()
                                                f.write(f"[Sound: {sound_id}]\n")
                                    elif re.match(r"@([^:]+):([^:]+)", line):
                                        char_expr_match = re.match(r"@([^:]+):([^:]+)", line)
                                        if char_expr_match:
                                            char_id = char_expr_match.group(1).strip()
                                            expression = char_expr_match.group(2).strip()
                                            f.write(f"{char_id} [{expression}]: ")
                                    elif include_commands_var.get():
                                        f.write(f"{line}\n")
                                    continue
                                
                                # Process choices
                                if line.startswith("->"):
                                    choice_text = line[2:].strip()
                                    f.write(f"- {choice_text}\n")
                                    continue
                                
                                # Regular text
                                f.write(f"{line}\n")
                            
                            f.write("\n\n")
                
                elif format_type == "HTML":
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.project_config.get('name', 'Visual Novel')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; }}
        .scene {{ background-color: #f0f0f0; padding: 10px; margin: 10px 0; }}
        .character {{ color: #900; font-weight: bold; }}
        .dialogue {{ margin-left: 20px; }}
        .choice {{ color: #060; font-style: italic; margin-left: 20px; }}
        .comment {{ color: #999; font-style: italic; }}
    </style>
</head>
<body>
    <h1>{self.project_config.get('name', 'Visual Novel')}</h1>
    <p>By {self.project_config.get('author', 'Unknown')}</p>
""")
                        
                        for script_file in script_files:
                            script_path = os.path.join(script_dir, script_file)
                            f.write(f'    <h2>{script_file}</h2>\n')
                            
                            with open(script_path, 'r', encoding='utf-8') as sf:
                                script_content = sf.read()
                                
                            # Process script content
                            lines = script_content.split("\n")
                            i = 0
                            
                            while i < len(lines):
                                line = lines[i].strip()
                                i += 1
                                
                                # Skip empty lines
                                if not line:
                                    continue
                                
                                # Include comments if requested
                                if line.startswith("#"):
                                    if include_comments_var.get():
                                        f.write(f'    <p class="comment">{line}</p>\n')
                                    continue
                                
                                # Process commands
                                if line.startswith("@"):
                                    if line.startswith("@scene:"):
                                        scene_match = re.match(r"@scene:([^:]+)(?::(.+))?", line)
                                        if scene_match:
                                            scene_id = scene_match.group(1).strip()
                                            f.write(f'    <div class="scene">[Scene: {scene_id}]</div>\n')
                                    elif line.startswith("@character:"):
                                        char_match = re.match(r"@character:([^:]+)", line)
                                        if char_match:
                                            char_id = char_match.group(1).strip()
                                            
                                            # Get dialogue
                                            if i < len(lines):
                                                dialogue = lines[i].strip()
                                                i += 1
                                                
                                                # Replace formatting
                                                dialogue = dialogue.replace("**", "<strong>").replace("**", "</strong>")
                                                dialogue = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", dialogue)
                                                
                                                f.write(f'    <p><span class="character">{char_id}:</span> <span class="dialogue">{dialogue}</span></p>\n')
                                    elif re.match(r"@([^:]+):([^:]+)", line) and not line.startswith("@bgm:") and not line.startswith("@sound:"):
                                        char_expr_match = re.match(r"@([^:]+):([^:]+)", line)
                                        if char_expr_match:
                                            char_id = char_expr_match.group(1).strip()
                                            expression = char_expr_match.group(2).strip()
                                            
                                            # Get dialogue
                                            if i < len(lines):
                                                dialogue = lines[i].strip()
                                                i += 1
                                                
                                                # Replace formatting
                                                dialogue = dialogue.replace("**", "<strong>").replace("**", "</strong>")
                                                dialogue = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", dialogue)
                                                
                                                f.write(f'    <p><span class="character">{char_id} [{expression}]:</span> <span class="dialogue">{dialogue}</span></p>\n')
                                    elif include_commands_var.get():
                                        if line.startswith("@bgm:"):
                                            bgm_match = re.match(r"@bgm:([^:]+)(?::(.+))?", line)
                                            if bgm_match:
                                                bgm_id = bgm_match.group(1).strip()
                                                f.write(f'    <p><em>[Music: {bgm_id}]</em></p>\n')
                                        elif line.startswith("@sound:"):
                                            sound_match = re.match(r"@sound:([^:]+)(?::(.+))?", line)
                                            if sound_match:
                                                sound_id = sound_match.group(1).strip()
                                                f.write(f'    <p><em>[Sound: {sound_id}]</em></p>\n')
                                    continue
                                
                                # Process choices
                                if line.startswith("->"):
                                    f.write('    <ul>\n')
                                    
                                    # First choice
                                    choice_text = line[2:].strip()
                                    f.write(f'        <li class="choice">{choice_text}</li>\n')
                                    
                                    # Get more choices
                                    while i < len(lines) and lines[i].startswith("->"):
                                        choice_text = lines[i][2:].strip()
                                        f.write(f'        <li class="choice">{choice_text}</li>\n')
                                        i += 1
                                    
                                    f.write('    </ul>\n')
                                    continue
                                
                                # Regular text
                                f.write(f'    <p>{line}</p>\n')
                            
                        f.write("""</body>
</html>""")
                
                elif format_type == "Markdown":
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"# {self.project_config.get('name', 'Visual Novel')}\n\n")
                        f.write(f"By {self.project_config.get('author', 'Unknown')}\n\n")
                        
                        for script_file in script_files:
                            script_path = os.path.join(script_dir, script_file)
                            f.write(f"## {script_file}\n\n")
                            
                            with open(script_path, 'r', encoding='utf-8') as sf:
                                script_content = sf.read()
                                
                            # Process script content
                            lines = script_content.split("\n")
                            i = 0
                            
                            while i < len(lines):
                                line = lines[i].strip()
                                i += 1
                                
                                # Skip empty lines
                                if not line:
                                    f.write("\n")
                                    continue
                                
                                # Include comments if requested
                                if line.startswith("#"):
                                    if include_comments_var.get():
                                        f.write(f"*{line}*\n\n")
                                    continue
                                
                                # Process commands
                                if line.startswith("@"):
                                    if line.startswith("@scene:"):
                                        scene_match = re.match(r"@scene:([^:]+)(?::(.+))?", line)
                                        if scene_match:
                                            scene_id = scene_match.group(1).strip()
                                            f.write(f"### Scene: {scene_id}\n\n")
                                    elif line.startswith("@character:"):
                                        char_match = re.match(r"@character:([^:]+)", line)
                                        if char_match:
                                            char_id = char_match.group(1).strip()
                                            
                                            # Get dialogue
                                            if i < len(lines):
                                                dialogue = lines[i].strip()
                                                i += 1
                                                f.write(f"**{char_id}:** {dialogue}\n\n")
                                    elif re.match(r"@([^:]+):([^:]+)", line) and not line.startswith("@bgm:") and not line.startswith("@sound:"):
                                        char_expr_match = re.match(r"@([^:]+):([^:]+)", line)
                                        if char_expr_match:
                                            char_id = char_expr_match.group(1).strip()
                                            expression = char_expr_match.group(2).strip()
                                            
                                            # Get dialogue
                                            if i < len(lines):
                                                dialogue = lines[i].strip()
                                                i += 1
                                                f.write(f"**{char_id} [{expression}]:** {dialogue}\n\n")
                                    elif include_commands_var.get():
                                        if line.startswith("@bgm:"):
                                            bgm_match = re.match(r"@bgm:([^:]+)(?::(.+))?", line)
                                            if bgm_match:
                                                bgm_id = bgm_match.group(1).strip()
                                                f.write(f"*[Music: {bgm_id}]*\n\n")
                                        elif line.startswith("@sound:"):
                                            sound_match = re.match(r"@sound:([^:]+)(?::(.+))?", line)
                                            if sound_match:
                                                sound_id = sound_match.group(1).strip()
                                                f.write(f"*[Sound: {sound_id}]*\n\n")
                                    continue
                                
                                # Process choices
                                if line.startswith("->"):
                                    # First choice
                                    choice_text = line[2:].strip()
                                    f.write(f"- *{choice_text}*\n")
                                    
                                    # Get more choices
                                    while i < len(lines) and lines[i].startswith("->"):
                                        choice_text = lines[i][2:].strip()
                                        f.write(f"- *{choice_text}*\n")
                                        i += 1
                                    
                                    f.write("\n")
                                    continue
                                
                                # Regular text
                                f.write(f"{line}\n\n")
                
                else:  # Game Script
                    # Compile the script to JSON format
                    compiled_script = {
                        "title": self.project_config.get("name", "Visual Novel"),
                        "author": self.project_config.get("author", "Unknown"),
                        "version": self.project_config.get("version", "0.1"),
                        "start": self.project_config.get("start_scene", "main"),
                        "nodes": {},
                        "variables": {}
                    }
                    
                    # Process each script file
                    for script_file in script_files:
                        script_path = os.path.join(script_dir, script_file)
                        
                        with open(script_path, 'r', encoding='utf-8') as f:
                            script_content = f.read()
                        
                        # Parse the script
                        self._parse_script_file(script_content, compiled_script, lambda x: None)
                    
                    # Save compiled script
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(compiled_script, f, indent=2)
                
                messagebox.showinfo("Export", f"Script exported successfully to:\n{output_file}")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export script: {str(e)}")
        
        ttk.Button(button_frame, text="Export", command=export_script).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_character_manager(self):
        """Show the character manager dialog"""
        # Switch to the characters tab
        self.right_notebook.select(self.characters_frame)
        
        # Refresh character list
        self._refresh_characters()
    
    def _show_scene_manager(self):
        """Show the scene manager dialog"""
        # Switch to the scenes tab
        self.right_notebook.select(self.scenes_frame)
        
        # Refresh scene list
        self._refresh_scenes()
    
    def _show_resource_manager(self):
        """Show the resource manager dialog"""
        # Switch to the resources tab
        self.right_notebook.select(self.resources_frame)
        
        # Refresh resource list
        self._refresh_resources()
    
    def _show_statistics(self):
        """Show statistics about the current script"""
        editor = self._get_current_editor()
        if not editor:
            messagebox.showinfo("Statistics", "Please open a script file first")
            return
        
        # Get the script content
        script_content = editor.get("1.0", tk.END)
        
        # Create a dialog to show statistics
        dialog = tk.Toplevel(self.root)
        dialog.title("Script Statistics")
        dialog.transient(self.root)
        dialog.geometry("400x500")
        
        # Stats frame
        stats_frame = ttk.LabelFrame(dialog, text="Statistics")
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Calculate statistics
        lines = script_content.split("\n")
        total_lines = len(lines)
        
        # Count non-empty lines
        content_lines = sum(1 for line in lines if line.strip())
        
        # Count words
        words = len(re.findall(r'\w+', script_content))
        
        # Count characters
        characters = len(script_content)
        
        # Count scenes
        scenes = len(re.findall(r"@scene:", script_content))
        
        # Count characters (people)
        character_matches = re.findall(r"@character:([^:]+)", script_content)
        characters_set = set(character_matches)
        
        # Count expressions
        expr_matches = re.findall(r"@([^:]+):([^:]+)", script_content)
        expr_set = set(match[1] for match in expr_matches if match[0] not in ["scene", "character", "bgm", "sound"])
        
        # Count dialogue lines
        dialogue_count = 0
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("@character:") or (re.match(r"@[^:]+:[^:]+", line) and 
                                               not line.startswith("@scene:") and 
                                               not line.startswith("@bgm:") and 
                                               not line.startswith("@sound:")):
                dialogue_count += 1
                
            i += 1
        
        # Count choices
        choice_matches = [line for line in lines if line.strip().startswith("->")]
        choices = len(choice_matches)
        
        # Average words per dialogue
        avg_words = words / dialogue_count if dialogue_count > 0 else 0
        
        # Create stats display
        ttk.Label(stats_frame, text=f"Total Lines: {total_lines}").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Content Lines: {content_lines}").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Word Count: {words}").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Character Count: {characters}").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Scenes: {scenes}").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Characters: {len(characters_set)}").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Expressions: {len(expr_set)}").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Dialogue Lines: {dialogue_count}").grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Choices: {choices}").grid(row=8, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_frame, text=f"Average Words per Dialogue: {avg_words:.1f}").grid(row=9, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Characters list
        chars_frame = ttk.LabelFrame(dialog, text="Characters")
        chars_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        chars_list = tk.Listbox(chars_frame, height=6)
        chars_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        for char in sorted(characters_set):
            chars_list.insert(tk.END, char)
        
        # Expressions list
        exprs_frame = ttk.LabelFrame(dialog, text="Expressions")
        exprs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        exprs_list = tk.Listbox(exprs_frame, height=6)
        exprs_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        for expr in sorted(expr_set):
            exprs_list.insert(tk.END, expr)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def _save_version(self):
        """Save a snapshot of the current file as a version"""
        editor = self._get_current_editor()
        if not editor:
            messagebox.showinfo("Version Control", "Please open a script file first")
            return
        
        # Get current tab info
        current_tab = self.editor_notebook.select()
        tab_index = self.editor_notebook.index(current_tab)
        tab_frame = self.editor_notebook.winfo_children()[tab_index]
        
        if not hasattr(tab_frame, 'file_path') or not tab_frame.file_path:
            messagebox.showinfo("Version Control", "Please save the file before creating a version")
            return
        
        # Create dialog for version info
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Version")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Version Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar(value=f"Version {len(self.version_history) + 1}")
        ttk.Entry(dialog, textvariable=name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(dialog, text="Description:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
        description_text = tk.Text(dialog, width=30, height=5)
        description_text.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        def create_version():
            version_name = name_var.get().strip()
            if not version_name:
                messagebox.showwarning("Warning", "Version name is required")
                return
                
            try:
                # Get content
                content = editor.get("1.0", tk.END)
                
                # Create version data
                version_data = {
                    "name": version_name,
                    "description": description_text.get("1.0", tk.END).strip(),
                    "timestamp": time.time(),
                    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "file_path": tab_frame.file_path,
                    "filename": os.path.basename(tab_frame.file_path)
                }
                
                # Generate version filename
                version_filename = f"{version_data['filename']}_{int(version_data['timestamp'])}.vn"
                version_path = os.path.join(self.project_dir, self.versions_dir, version_filename)
                
                # Save version file
                with open(version_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Add path to version data
                version_data["version_path"] = version_path
                
                # Add to version history
                self.version_history.append(version_data)
                
                # Save version history to project
                if 'versions' not in self.project_config:
                    self.project_config['versions'] = []
                
                self.project_config['versions'].append(version_data)
                self._save_project()
                
                messagebox.showinfo("Version Control", f"Version '{version_name}' saved successfully")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save version: {str(e)}")
        
        ttk.Button(button_frame, text="Save Version", command=create_version).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _load_version(self):
        """Load a previously saved version"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Load version history from project
        if 'versions' in self.project_config:
            self.version_history = self.project_config['versions']
        
        if not self.version_history:
            messagebox.showinfo("Version Control", "No versions available")
            return
        
        # Create dialog to select version
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Version")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("600x400")
        
        # Create a listbox for versions
        ttk.Label(dialog, text="Select a version:").pack(anchor=tk.W, padx=10, pady=5)
        
        versions_frame = ttk.Frame(dialog)
        versions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        versions_list = ttk.Treeview(versions_frame, columns=("date", "file"))
        versions_list.heading("#0", text="Version")
        versions_list.heading("date", text="Date")
        versions_list.heading("file", text="File")
        versions_list.column("#0", width=150)
        versions_list.column("date", width=150)
        versions_list.column("file", width=150)
        
        versions_scrollbar = ttk.Scrollbar(versions_frame, orient=tk.VERTICAL, command=versions_list.yview)
        versions_list.configure(yscrollcommand=versions_scrollbar.set)
        
        versions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        versions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Fill versions list
        for version in self.version_history:
            versions_list.insert("", "end", text=version["name"], 
                              values=(version["date"], version["filename"]))
        
        # Description frame
        desc_frame = ttk.LabelFrame(dialog, text="Description")
        desc_frame.pack(fill=tk.X, padx=10, pady=5)
        
        desc_text = tk.Text(desc_frame, width=40, height=5, wrap=tk.WORD)
        desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        desc_text.config(state=tk.DISABLED)
        
        # Update description when selection changes
        def on_select(event):
            selected = versions_list.focus()
            if selected:
                idx = versions_list.index(selected)
                if 0 <= idx < len(self.version_history):
                    version = self.version_history[idx]
                    
                    desc_text.config(state=tk.NORMAL)
                    desc_text.delete("1.0", tk.END)
                    desc_text.insert("1.0", version["description"])
                    desc_text.config(state=tk.DISABLED)
        
        versions_list.bind("<<TreeviewSelect>>", on_select)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def load_selected_version():
            selected = versions_list.focus()
            if not selected:
                messagebox.showinfo("Version Control", "Please select a version to load")
                return
                
            idx = versions_list.index(selected)
            if 0 <= idx < len(self.version_history):
                version = self.version_history[idx]
                
                try:
                    # Check if version file exists
                    if "version_path" not in version or not os.path.exists(version["version_path"]):
                        messagebox.showerror("Error", "Version file not found")
                        return
                    
                    # Load version content
                    with open(version["version_path"], 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check if the file is open
                    file_path = version["file_path"]
                    file_open = False
                    tab_index = -1
                    
                    for i, tab_id in enumerate(self.editor_notebook.tabs()):
                        tab_frame = self.editor_notebook.winfo_children()[i]
                        if hasattr(tab_frame, 'file_path') and tab_frame.file_path == file_path:
                            file_open = True
                            tab_index = i
                            break
                    
                    if file_open:
                        # Confirm replacement
                        if messagebox.askyesno("Version Control", 
                                              f"Replace current content of {os.path.basename(file_path)} with version '{version['name']}'?"):
                            # Replace content
                            tab_frame = self.editor_notebook.winfo_children()[tab_index]
                            tab_frame.text_editor.delete("1.0", tk.END)
                            tab_frame.text_editor.insert("1.0", content)
                            
                            # Switch to the tab
                            self.editor_notebook.select(tab_index)
                    else:
                        # Open in new tab
                        if messagebox.askyesno("Version Control", 
                                              f"Open version '{version['name']}' in a new tab?"):
                            # Create new tab with version content
                            file_name = f"{os.path.basename(file_path)} (Version: {version['name']})"
                            text_editor = self._create_editor_tab(file_name, content)
                    
                    dialog.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load version: {str(e)}")
        
        def compare_with_current():
            selected = versions_list.focus()
            if not selected:
                messagebox.showinfo("Version Control", "Please select a version to compare")
                return
                
            idx = versions_list.index(selected)
            if 0 <= idx < len(self.version_history):
                version = self.version_history[idx]
                
                try:
                    # Check if version file exists
                    if "version_path" not in version or not os.path.exists(version["version_path"]):
                        messagebox.showerror("Error", "Version file not found")
                        return
                    
                    # Load version content
                    with open(version["version_path"], 'r', encoding='utf-8') as f:
                        version_content = f.read()
                    
                    # Check if the file is open
                    file_path = version["file_path"]
                    file_open = False
                    tab_index = -1
                    
                    for i, tab_id in enumerate(self.editor_notebook.tabs()):
                        tab_frame = self.editor_notebook.winfo_children()[i]
                        if hasattr(tab_frame, 'file_path') and tab_frame.file_path == file_path:
                            file_open = True
                            tab_index = i
                            break
                    
                    if file_open:
                        # Get current content
                        tab_frame = self.editor_notebook.winfo_children()[tab_index]
                        current_content = tab_frame.text_editor.get("1.0", tk.END)
                        
                        # Show comparison
                        self._show_comparison(version["name"], version_content, 
                                            os.path.basename(file_path), current_content)
                    else:
                        # Ask if user wants to open the file
                        if messagebox.askyesno("Version Control", 
                                              f"File {os.path.basename(file_path)} is not open. Open it for comparison?"):
                            # Open the file
                            self._open_file(file_path)
                            
                            # Get current content
                            tab_frame = self.editor_notebook.winfo_children()[self.editor_notebook.index(self.editor_notebook.select())]
                            current_content = tab_frame.text_editor.get("1.0", tk.END)
                            
                            # Show comparison
                            self._show_comparison(version["name"], version_content, 
                                                os.path.basename(file_path), current_content)
                            
                            dialog.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to compare version: {str(e)}")
        
        ttk.Button(button_frame, text="Load Version", command=load_selected_version).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Compare with Current", command=compare_with_current).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _compare_versions(self):
        """Compare two versions of a script"""
        if not self.project_dir:
            messagebox.showerror("Error", "No project is open")
            return
        
        # Load version history from project
        if 'versions' in self.project_config:
            self.version_history = self.project_config['versions']
        
        if len(self.version_history) < 2:
            messagebox.showinfo("Version Control", "Need at least two versions to compare")
            return
        
        # Create dialog to select versions
        dialog = tk.Toplevel(self.root)
        dialog.title("Compare Versions")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("600x400")
        
        # Create a frame for version selection
        select_frame = ttk.Frame(dialog)
        select_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Version 1 selection
        ttk.Label(select_frame, text="Version 1:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        v1_names = [v["name"] for v in self.version_history]
        v1_var = tk.StringVar(value=v1_names[0] if v1_names else "")
        ttk.Combobox(select_frame, textvariable=v1_var, values=v1_names, width=30).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Version 2 selection
        ttk.Label(select_frame, text="Version 2:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        v2_var = tk.StringVar(value=v1_names[-1] if len(v1_names) > 1 else "")
        ttk.Combobox(select_frame, textvariable=v2_var, values=v1_names, width=30).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def compare_selected():
            v1_name = v1_var.get()
            v2_name = v2_var.get()
            
            if v1_name == v2_name:
                messagebox.showwarning("Warning", "Please select different versions to compare")
                return
                
            try:
                # Find version data
                v1_data = None
                v2_data = None
                
                for v in self.version_history:
                    if v["name"] == v1_name:
                        v1_data = v
                    if v["name"] == v2_name:
                        v2_data = v
                
                if not v1_data or not v2_data:
                    messagebox.showerror("Error", "Selected version not found")
                    return
                
                # Check if version files exist
                if "version_path" not in v1_data or not os.path.exists(v1_data["version_path"]):
                    messagebox.showerror("Error", f"Version file for '{v1_name}' not found")
                    return
                    
                if "version_path" not in v2_data or not os.path.exists(v2_data["version_path"]):
                    messagebox.showerror("Error", f"Version file for '{v2_name}' not found")
                    return
                
                # Load version content
                with open(v1_data["version_path"], 'r', encoding='utf-8') as f:
                    v1_content = f.read()
                    
                with open(v2_data["version_path"], 'r', encoding='utf-8') as f:
                    v2_content = f.read()
                
                # Show comparison
                self._show_comparison(v1_name, v1_content, v2_name, v2_content)
                
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to compare versions: {str(e)}")
        
        ttk.Button(button_frame, text="Compare", command=compare_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _show_comparison(self, title1, content1, title2, content2):
        """Show a comparison between two text contents"""
        # Create comparison dialog
        comp_dialog = tk.Toplevel(self.root)
        comp_dialog.title(f"Compare: {title1} vs {title2}")
        comp_dialog.geometry("800x600")
        
        # Split view for comparison
        comp_paned = tk.PanedWindow(comp_dialog, orient=tk.HORIZONTAL)
        comp_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side (version 1)
        left_frame = ttk.LabelFrame(comp_paned, text=title1)
        left_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD)
        left_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right side (version 2)
        right_frame = ttk.LabelFrame(comp_paned, text=title2)
        right_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD)
        right_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        comp_paned.add(left_frame)
        comp_paned.add(right_frame)
        
        # Configure text tags for diff highlighting
        left_text.tag_configure("diff_add", background="#e6ffed")
        left_text.tag_configure("diff_del", background="#ffeef0")
        
        right_text.tag_configure("diff_add", background="#e6ffed")
        right_text.tag_configure("diff_del", background="#ffeef0")
        
        # Compute diff and display
        lines1 = content1.splitlines()
        lines2 = content2.splitlines()
        
        # Use difflib to compute the differences
        diff = difflib.unified_diff(lines1, lines2, lineterm='')
        
        # Skip the first two lines (headers)
        next(diff, None)
        next(diff, None)
        
        # Process diff
        left_text.insert(tk.END, content1)
        right_text.insert(tk.END, content2)
        
        # Find and highlight differences
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        for tag, i1, i2, j1, j2 in reversed(matcher.get_opcodes()):
            if tag == 'replace' or tag == 'delete':
                # Highlight in left text
                for line in range(i1, i2):
                    left_text.tag_add("diff_del", f"{line+1}.0", f"{line+1}.end")
            
            if tag == 'replace' or tag == 'insert':
                # Highlight in right text
                for line in range(j1, j2):
                    right_text.tag_add("diff_add", f"{line+1}.0", f"{line+1}.end")
        
        # Synchronize scrolling
        def sync_scroll(*args):
            left_text.yview_moveto(args[0])
            return "break"
            
        def on_left_scroll(*args):
            left_text.yview_moveto(float(args[0]))
            right_text.yview_moveto(float(args[0]))
            return "break"
            
        def on_right_scroll(*args):
            right_text.yview_moveto(float(args[0]))
            left_text.yview_moveto(float(args[0]))
            return "break"
        
        left_text.config(yscrollcommand=on_left_scroll)
        right_text.config(yscrollcommand=on_right_scroll)
        
        # Bottom buttons
        button_frame = ttk.Frame(comp_dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Close", command=comp_dialog.destroy).pack()
    
    def _show_documentation(self):
        """Show documentation for the VN Editor"""
        doc_dialog = tk.Toplevel(self.root)
        doc_dialog.title("VN Editor Documentation")
        doc_dialog.geometry("700x500")
        
        # Create notebook for documentation sections
        doc_notebook = ttk.Notebook(doc_dialog)
        doc_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Overview tab
        overview_frame = ttk.Frame(doc_notebook)
        overview_text = scrolledtext.ScrolledText(overview_frame, wrap=tk.WORD)
        overview_text.pack(fill=tk.BOTH, expand=True)
        overview_text.insert(tk.END, """# VN Editor Documentation

VN Editor is a comprehensive editor for creating visual novel scripts. This documentation will help you get started and make the most of the editor's features.

## Main Features

- Script editing with syntax highlighting
- Character and scene management
- Resource management
- Script validation and preview
- Version control for scripts
- Export to various formats

Use the tabs in this documentation to learn more about specific features.
""")
        overview_text.config(state=tk.DISABLED)
        doc_notebook.add(overview_frame, text="Overview")
        
        # Script syntax tab
        syntax_frame = ttk.Frame(doc_notebook)
        syntax_text = scrolledtext.ScrolledText(syntax_frame, wrap=tk.WORD)
        syntax_text.pack(fill=tk.BOTH, expand=True)
        syntax_text.insert(tk.END, """# Script Syntax

VN Editor uses a simple, intuitive syntax for writing visual novel scripts.

## Basic Commands

- `@scene:scene_id` - Set the background scene
- `@scene:scene_id:transition` - Set the scene with transition
- `@character:character_id` - Set the speaking character
- `@character_id:expression` - Set character with expression
- `@bgm:music_id` - Play background music
- `@bgm:music_id:fade_time` - Play music with fade-in
- `@sound:sound_id` - Play a sound effect

## Dialogue

After a character declaration, simply write the dialogue text on the next line:

```
@character:protagonist
Hello, world! This is my first visual novel.
```

## Choices

Choices are created using the `->` syntax:

```
-> Go to the park
-> Stay at home
-> Call a friend
```

## Text Formatting

- `**bold text**` - Bold text
- `*italic text*` - Italic text

## Comments

Comments are preceded by the `#` character:

```
# This is a comment
## This is a second-level comment
```
""")
        syntax_text.config(state=tk.DISABLED)
        doc_notebook.add(syntax_frame, text="Script Syntax")
        
        # Editor features tab
        features_frame = ttk.Frame(doc_notebook)
        features_text = scrolledtext.ScrolledText(features_frame, wrap=tk.WORD)
        features_text.pack(fill=tk.BOTH, expand=True)
        features_text.insert(tk.END, """# Editor Features

## Project Management

- **New Project**: Create a new visual novel project
- **Open Project**: Open an existing project
- **Project Settings**: Configure project properties

## File Operations

- **New File**: Create a new script file
- **Open File**: Open an existing script file
- **Save/Save As**: Save the current script

## Editing

- **Undo/Redo**: Undo or redo changes
- **Cut/Copy/Paste**: Standard editing operations
- **Find/Replace**: Search for text in the script

## Script Tools

- **Validate Script**: Check your script for syntax errors
- **Preview**: See how your script will look in the game
- **Compile Script**: Convert your script to the game format
- **Export Script**: Export to different formats (text, HTML, Markdown)

## Management

- **Character Manager**: Create and edit characters
- **Scene Manager**: Create and edit scenes
- **Resource Manager**: Manage images, music, and sounds

## Version Control

- **Save Version**: Save a snapshot of your script
- **Load Version**: Restore a previous version
- **Compare Versions**: Compare different versions of your script
""")
        features_text.config(state=tk.DISABLED)
        doc_notebook.add(features_frame, text="Features")
        
        # Tips and tricks tab
        tips_frame = ttk.Frame(doc_notebook)
        tips_text = scrolledtext.ScrolledText(tips_frame, wrap=tk.WORD)
        tips_text.pack(fill=tk.BOTH, expand=True)
        tips_text.insert(tk.END, """# Tips and Tricks

## Efficient Workflow

1. **Use keyboard shortcuts**: 
   - Ctrl+S to save
   - Ctrl+Z/Y for undo/redo
   - Ctrl+F for find

2. **Character dialogue shortcut**: Double-click a character in the Characters panel to insert it.

3. **Tab management**: Use multiple tabs to organize different parts of your story.

4. **Regular validation**: Use the Validate Script function frequently to catch errors.

5. **Preview often**: Check how your script looks in the Preview tab.

## Organization Tips

1. **Split large stories**: Break your story into multiple script files for easier management.

2. **Use comments**: Add comments to mark important sections and explain complex choices.

3. **Consistent naming**: Use consistent naming conventions for scenes, characters, and resources.

4. **Save versions**: Create versions at important milestones in your story development.

## Avoiding Common Issues

1. **Orphaned dialogue**: Make sure all dialogue has a character attribution.

2. **Missing resources**: Verify that all referenced scenes, characters, and sounds exist.

3. **Unclosed formatting**: Check that all formatting tags (bold, italic) are properly closed.

4. **Choice flow**: Ensure that each choice leads to a valid story path.
""")
        tips_text.config(state=tk.DISABLED)
        doc_notebook.add(tips_frame, text="Tips & Tricks")
        
        # Close button
        ttk.Button(doc_dialog, text="Close", command=doc_dialog.destroy).pack(pady=10)
    
    def _show_syntax_help(self):
        """Show a quick reference for script syntax"""
        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("Script Syntax Reference")
        help_dialog.geometry("500x400")
        
        # Create a text widget for the syntax help
        help_text = scrolledtext.ScrolledText(help_dialog, wrap=tk.WORD)
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add syntax information
        help_text.insert(tk.END, """# VN Script Syntax Quick Reference

## Scene Commands
@scene:scene_id                 # Change scene
@scene:scene_id:transition      # Change scene with transition

## Character Commands
@character:character_id         # Set speaking character
character dialogue text         # Dialogue on the next line

@character_id:expression        # Character with expression
character dialogue text         # Dialogue on the next line

## Choice Commands
-> Choice option 1              # Create a choice
-> Choice option 2
-> Choice option 3

## Audio Commands
@bgm:music_id                   # Play background music
@bgm:music_id:fade_time         # Play music with fade-in
@bgm:music_id:fade_time:noloop  # Play music once

@sound:sound_id                 # Play sound effect
@sound:sound_id:volume          # Play sound with volume (0-100)

## Text Formatting
**bold text**                   # Bold text
*italic text*                   # Italic text

## Comments
# Comment text                  # Single line comment
""")
        
        help_text.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(help_dialog, text="Close", command=help_dialog.destroy).pack(pady=10)
    
    def _show_about(self):
        """Show about dialog"""
        about_dialog = tk.Toplevel(self.root)
        about_dialog.title("About VN Editor")
        about_dialog.transient(self.root)
        about_dialog.grab_set()
        about_dialog.geometry("400x300")
        
        # App title
        ttk.Label(about_dialog, text="VN Editor", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Version
        ttk.Label(about_dialog, text="Version 1.0").pack()
        
        # Description
        desc_frame = ttk.Frame(about_dialog)
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        desc_text = """VN Editor is a comprehensive script editor for visual novel game development.

Features:
• Script editing with syntax highlighting
• Character and scene management
• Resource management
• Script validation and preview
• Version control
• Export to various formats

Created as a companion tool for the Visual Novel Engine."""
        
        ttk.Label(desc_frame, text=desc_text, wraplength=360, justify=tk.CENTER).pack(fill=tk.BOTH, expand=True)
        
        # Copyright
        ttk.Label(about_dialog, text="© 2023 Visual Novel Engine").pack(pady=5)
        
        # Close button
        ttk.Button(about_dialog, text="Close", command=about_dialog.destroy).pack(pady=10)
    
    def _confirm_exit(self):
        """Confirm exit if there are unsaved changes"""
        if self.text_modified:
            if messagebox.askyesno("Unsaved Changes", 
                                   "You have unsaved changes. Exit without saving?"):
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Run the editor application"""
        self.root.mainloop()


def main():
    """Main function to run the VN Editor"""
    editor = VNEditor()
    editor.run()


if __name__ == "__main__":
    main()
