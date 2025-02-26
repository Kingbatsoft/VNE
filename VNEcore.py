"""
VNEngine - A modular Visual Novel engine written in Python
Core architecture and component definitions
"""

import pygame
import json
import os
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable

class VNEngine:
    """Main engine class that coordinates all components"""
    
    def __init__(self, resolution: Tuple[int, int] = (1280, 720), title: str = "Visual Novel"):
        """Initialize the visual novel engine with basic settings"""
        # Initialize pygame
        pygame.init()
        pygame.mixer.init()
        
        # Set up the screen
        self.screen = pygame.display.set_mode(resolution)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.running = True
        
        # Initialize core components
        self.resource_manager = ResourceManager()
        self.story_manager = StoryManager(self)
        self.character_manager = CharacterManager(self)
        self.scene_manager = SceneManager(self)
        self.audio_manager = AudioManager(self)
        self.gui_manager = GUIManager(self)
        self.save_manager = SaveLoadManager(self)
        
        # Game state
        self.game_vars = {}  # For storing game variables that affect the story
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("VNEngine")
        
    def load_game(self, script_path: str) -> None:
        """Load the game from a script file"""
        self.logger.info(f"Loading game from: {script_path}")
        self.story_manager.load_script(script_path)
        
        # Extract and load required resources
        resources = self.story_manager.get_required_resources()
        for res_type, res_items in resources.items():
            for res_id, res_path in res_items.items():
                self.resource_manager.load_resource(res_id, res_path, res_type)
        
        # Initialize the game
        self.story_manager.start()
    
    def run(self) -> None:
        """Main game loop"""
        self.logger.info("Starting main game loop")
        
        while self.running:
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.handle_event(event)
            
            # Update game state
            self.update()
            
            # Render the game
            self.render()
            
            # Maintain frame rate
            self.clock.tick(self.fps)
        
        self.quit()
    
    def handle_event(self, event: pygame.event.Event) -> None:
        """Process pygame events"""
        # Let the GUI handle the event first (e.g., buttons, choices)
        if self.gui_manager.handle_event(event):
            return
        
        # Handle navigation (advancing text, etc.)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self.story_manager.advance_dialogue()
            elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.save_manager.quick_save()
                self.gui_manager.show_notification("Game saved")
            elif event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.save_manager.quick_load()
                self.gui_manager.show_notification("Game loaded")
    
    def update(self) -> None:
        """Update game logic"""
        # Get current state from story manager
        state = self.story_manager.get_current_state()
        
        # Update scene if needed
        if 'scene' in state:
            self.scene_manager.set_scene(state['scene'])
        
        # Update characters
        for char_id, char_data in state.get('characters', {}).items():
            if char_data.get('visible', True):
                self.character_manager.show_character(
                    char_id, 
                    char_data.get('position', 'center'),
                    char_data.get('expression', 'neutral')
                )
            else:
                self.character_manager.hide_character(char_id)
        
        # Update audio
        if 'bgm' in state:
            self.audio_manager.play_bgm(state['bgm'], fade_in=state.get('bgm_fade_in', 0))
        
        if 'sound' in state:
            self.audio_manager.play_sound(state['sound'])
        
        # Update dialogue and choices
        if 'dialogue' in state:
            self.gui_manager.show_dialogue(
                state['dialogue']['text'],
                state['dialogue'].get('character'),
                state['dialogue'].get('speed', 1.0)
            )
        
        if 'choices' in state:
            self.gui_manager.show_choices(state['choices'])
    
    def render(self) -> None:
        """Render the game screen"""
        # Clear screen
        self.screen.fill((0, 0, 0))
        
        # Draw scene background
        self.scene_manager.render(self.screen)
        
        # Draw characters
        self.character_manager.render(self.screen)
        
        # Draw GUI elements
        self.gui_manager.render(self.screen)
        
        # Update display
        pygame.display.flip()
    
    def quit(self) -> None:
        """Clean up and exit the game"""
        self.logger.info("Shutting down engine")
        pygame.quit()
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a game variable"""
        self.game_vars[name] = value
        self.logger.debug(f"Set variable: {name} = {value}")
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a game variable"""
        return self.game_vars.get(name, default)


class ResourceManager:
    """Handles loading and managing game resources like images, sounds, etc."""
    
    def __init__(self):
        """Initialize the resource manager"""
        self.resources = {}  # Dictionary to store all resources
        self.resource_paths = {}  # Dictionary to store paths to resources
        
        # Create resource directories if they don't exist
        self.resource_dirs = {
            'images': 'resources/images',
            'backgrounds': 'resources/backgrounds',
            'characters': 'resources/characters',
            'audio': 'resources/audio',
            'scripts': 'resources/scripts'
        }
        
        for dir_path in self.resource_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
        
        self.logger = logging.getLogger("ResourceManager")
    
    def load_resource(self, resource_id: str, file_path: str, resource_type: str) -> bool:
        """
        Load a resource from file
        
        Args:
            resource_id: Unique identifier for the resource
            file_path: Path to the resource file
            resource_type: Type of resource (image, sound, etc.)
            
        Returns:
            bool: True if resource was loaded successfully
        """
        self.logger.info(f"Loading resource: {resource_id} from {file_path}")
        
        try:
            # Store the path for future reference
            self.resource_paths[resource_id] = file_path
            
            # Load different resource types
            if resource_type == 'image' or resource_type == 'background':
                self.resources[resource_id] = pygame.image.load(file_path).convert_alpha()
            
            elif resource_type == 'character':
                # For characters, load all expressions from a directory or config
                if os.path.isdir(file_path):
                    self.resources[resource_id] = {}
                    for expr_file in os.listdir(file_path):
                        if expr_file.endswith(('.png', '.jpg', '.bmp')):
                            expr_name = os.path.splitext(expr_file)[0]
                            expr_path = os.path.join(file_path, expr_file)
                            self.resources[resource_id][expr_name] = pygame.image.load(expr_path).convert_alpha()
                else:
                    # Assume it's a single character image
                    self.resources[resource_id] = {'default': pygame.image.load(file_path).convert_alpha()}
            
            elif resource_type == 'sound':
                self.resources[resource_id] = pygame.mixer.Sound(file_path)
            
            elif resource_type == 'music' or resource_type == 'bgm':
                # Just store the path for music, load when needed
                self.resources[resource_id] = file_path
            
            elif resource_type == 'script':
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.resources[resource_id] = f.read()
            
            else:
                self.logger.warning(f"Unknown resource type: {resource_type}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load resource {resource_id}: {str(e)}")
            return False
    
    def get_resource(self, resource_id: str) -> Any:
        """Get a loaded resource by its ID"""
        if resource_id not in self.resources:
            self.logger.warning(f"Resource not found: {resource_id}")
            return None
        
        return self.resources[resource_id]
    
    def unload_resource(self, resource_id: str) -> bool:
        """Unload a resource to free memory"""
        if resource_id in self.resources:
            del self.resources[resource_id]
            self.logger.info(f"Unloaded resource: {resource_id}")
            return True
        return False


class StoryManager:
    """Handles the visual novel's story, dialogue, and branching choices"""
    
    def __init__(self, engine):
        """Initialize the story manager"""
        self.engine = engine
        self.script = None
        self.current_node = None
        self.dialogue_history = []
        self.script_parser = ScriptParser()
        self.logger = logging.getLogger("StoryManager")
    
    def load_script(self, script_path: str) -> bool:
        """Load and parse a script file"""
        try:
            # Load the script content
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            # Parse the script
            self.script = self.script_parser.parse(script_content)
            self.logger.info(f"Script loaded: {len(self.script['nodes'])} nodes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading script: {str(e)}")
            return False
    
    def start(self) -> None:
        """Start the story from the beginning"""
        if not self.script:
            self.logger.error("Cannot start story: No script loaded")
            return
        
        # Start from the first node
        start_node = self.script['start']
        self.current_node = start_node
        self.logger.info(f"Starting story at node: {start_node}")
        
        # Initialize game variables
        for var_name, var_value in self.script.get('variables', {}).items():
            self.engine.set_variable(var_name, var_value)
    
    def advance_dialogue(self) -> None:
        """Move to the next dialogue or handle choices"""
        if not self.current_node:
            return
            
        node = self.script['nodes'][self.current_node]
        
        # If this node has a "next" property, go to that node
        if 'next' in node:
            self._go_to_node(node['next'])
        
        # If this is a choice node, wait for player input
        elif node['type'] == 'choice':
            # Choices are handled by GUI events
            pass
        
        # If this is an end node, do nothing
        elif node['type'] == 'end':
            self.logger.info("Reached story end")
            # Maybe show credits or return to title screen
    
    def make_choice(self, choice_index: int) -> None:
        """Handle a player choice"""
        if not self.current_node:
            return
            
        node = self.script['nodes'][self.current_node]
        
        if node['type'] != 'choice' or choice_index >= len(node['choices']):
            self.logger.warning(f"Invalid choice: {choice_index}")
            return
        
        choice = node['choices'][choice_index]
        
        # Execute any actions for this choice
        if 'set' in choice:
            for var_name, var_value in choice['set'].items():
                self.engine.set_variable(var_name, var_value)
        
        # Go to the target node
        self._go_to_node(choice['target'])
    
    def _go_to_node(self, node_id: str) -> None:
        """Navigate to a specific node in the story"""
        if node_id not in self.script['nodes']:
            self.logger.error(f"Node not found: {node_id}")
            return
        
        self.current_node = node_id
        node = self.script['nodes'][node_id]
        
        # If this is a conditional node, evaluate the condition
        if node['type'] == 'condition':
            condition = node['condition']
            var_name = condition['variable']
            var_value = self.engine.get_variable(var_name)
            
            if condition['operator'] == '==':
                result = var_value == condition['value']
            elif condition['operator'] == '!=':
                result = var_value != condition['value']
            elif condition['operator'] == '>':
                result = var_value > condition['value']
            elif condition['operator'] == '<':
                result = var_value < condition['value']
            elif condition['operator'] == '>=':
                result = var_value >= condition['value']
            elif condition['operator'] == '<=':
                result = var_value <= condition['value']
            else:
                self.logger.error(f"Unknown operator: {condition['operator']}")
                result = False
            
            # Go to the appropriate branch
            next_node = node['true'] if result else node['false']
            self._go_to_node(next_node)
        
        # If it's a set variable node, set the variable and continue
        elif node['type'] == 'set':
            for var_name, var_value in node['variables'].items():
                self.engine.set_variable(var_name, var_value)
            
            if 'next' in node:
                self._go_to_node(node['next'])
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get the current state of the story for rendering"""
        if not self.current_node:
            return {}
            
        node = self.script['nodes'][self.current_node]
        state = {}
        
        # Add scene information
        if 'scene' in node:
            state['scene'] = node['scene']
        
        # Add character information
        if 'characters' in node:
            state['characters'] = node['characters']
        
        # Add audio information
        if 'bgm' in node:
            state['bgm'] = node['bgm']
            if 'bgm_fade_in' in node:
                state['bgm_fade_in'] = node['bgm_fade_in']
        
        if 'sound' in node:
            state['sound'] = node['sound']
        
        # Add dialogue information
        if node['type'] == 'dialogue':
            state['dialogue'] = {
                'text': node['text'],
                'character': node.get('character'),
                'speed': node.get('text_speed', 1.0)
            }
        
        # Add choice information
        elif node['type'] == 'choice':
            state['dialogue'] = {
                'text': node.get('text', ''),
                'character': node.get('character'),
                'speed': node.get('text_speed', 1.0)
            }
            
            state['choices'] = [choice['text'] for choice in node['choices']]
        
        return state
    
    def get_required_resources(self) -> Dict[str, Dict[str, str]]:
        """Extract all required resources from the script"""
        if not self.script:
            return {}
            
        resources = {
            'image': {},
            'background': {},
            'character': {},
            'sound': {},
            'music': {}
        }
        
        # Go through all nodes to find resources
        for node_id, node in self.script['nodes'].items():
            # Backgrounds
            if 'scene' in node:
                scene_id = node['scene']
                if scene_id not in resources['background']:
                    resources['background'][scene_id] = f"resources/backgrounds/{scene_id}.png"
            
            # Characters
            if 'characters' in node:
                for char_id, char_data in node['characters'].items():
                    if char_id not in resources['character']:
                        resources['character'][char_id] = f"resources/characters/{char_id}"
            
            # Music
            if 'bgm' in node:
                bgm_id = node['bgm']
                if bgm_id not in resources['music']:
                    resources['music'][bgm_id] = f"resources/audio/{bgm_id}.ogg"
            
            # Sound effects
            if 'sound' in node:
                sound_id = node['sound']
                if sound_id not in resources['sound']:
                    resources['sound'][sound_id] = f"resources/audio/{sound_id}.wav"
        
        return resources


class ScriptParser:
    """Parses visual novel script files into a format usable by the engine"""
    
    def __init__(self):
        """Initialize the script parser"""
        self.logger = logging.getLogger("ScriptParser")
    
    def parse(self, script_content: str) -> Dict[str, Any]:
        """
        Parse a script string into a structured format
        
        This is a simple implementation for demonstration purposes.
        A real implementation would use a more robust parsing approach.
        """
        try:
            # For simplicity, assume the script is in JSON format
            # A real implementation might use a custom language or format
            script_data = json.loads(script_content)
            
            # Validate the script structure
            if 'nodes' not in script_data:
                raise ValueError("Script missing 'nodes' section")
                
            if 'start' not in script_data:
                raise ValueError("Script missing 'start' node reference")
                
            if script_data['start'] not in script_data['nodes']:
                raise ValueError(f"Start node '{script_data['start']}' not found in nodes")
            
            return script_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Script parsing error: {str(e)}")
            raise


class CharacterManager:
    """Manages character sprites, expressions, and positions"""
    
    def __init__(self, engine):
        """Initialize the character manager"""
        self.engine = engine
        self.characters = {}  # Current state of characters
        self.logger = logging.getLogger("CharacterManager")
    
    def show_character(self, character_id: str, position: str, expression: str = 'neutral') -> None:
        """Show a character on screen with the given expression at the specified position"""
        self.logger.debug(f"Showing character: {character_id}, {expression} at {position}")
        
        # Get character sprite
        character_resource = self.engine.resource_manager.get_resource(character_id)
        
        if not character_resource:
            self.logger.warning(f"Character resource not found: {character_id}")
            return
        
        # Calculate position
        x, y = self._get_position_coordinates(position)
        
        # Store character state
        self.characters[character_id] = {
            'resource': character_resource,
            'expression': expression,
            'position': (x, y),
            'visible': True
        }
    
    def hide_character(self, character_id: str) -> None:
        """Hide a character from the screen"""
        if character_id in self.characters:
            self.characters[character_id]['visible'] = False
            self.logger.debug(f"Hiding character: {character_id}")
    
    def _get_position_coordinates(self, position: str) -> Tuple[int, int]:
        """Convert a position name to screen coordinates"""
        screen_width, screen_height = self.engine.screen.get_size()
        
        # Vertical position - usually at bottom third of screen
        y = int(screen_height * 0.75)
        
        # Horizontal position
        if position == 'left':
            x = int(screen_width * 0.25)
        elif position == 'center':
            x = int(screen_width * 0.5)
        elif position == 'right':
            x = int(screen_width * 0.75)
        else:
            # Try to parse custom position like "0.4"
            try:
                x = int(screen_width * float(position))
            except ValueError:
                x = int(screen_width * 0.5)  # Default to center
        
        return x, y
    
    def render(self, screen: pygame.Surface) -> None:
        """Render all visible characters to the screen"""
        for char_id, char_data in self.characters.items():
            if not char_data['visible']:
                continue
                
            char_resource = char_data['resource']
            expression = char_data['expression']
            position = char_data['position']
            
            # Get the right expression sprite
            if isinstance(char_resource, dict):
                # Use the requested expression or default to 'neutral'
                if expression in char_resource:
                    sprite = char_resource[expression]
                elif 'neutral' in char_resource:
                    sprite = char_resource['neutral']
                    self.logger.warning(f"Expression '{expression}' not found for {char_id}, using 'neutral'")
                else:
                    # Just use the first available expression
                    sprite = next(iter(char_resource.values()))
                    self.logger.warning(f"No suitable expression found for {char_id}")
            else:
                # If it's not a dict, assume it's a single image
                sprite = char_resource
            
            # Calculate position (center the sprite at the position point)
            x, y = position
            x -= sprite.get_width() // 2
            
            # Draw the character
            screen.blit(sprite, (x, y))


class SceneManager:
    """Manages background scenes and transitions"""
    
    def __init__(self, engine):
        """Initialize the scene manager"""
        self.engine = engine
        self.current_scene = None
        self.current_transition = None
        self.transition_progress = 0
        self.logger = logging.getLogger("SceneManager")
    
    def set_scene(self, scene_id: str, transition: str = None) -> None:
        """Set the current scene with optional transition effect"""
        self.logger.debug(f"Setting scene: {scene_id} with transition: {transition}")
        
        # Get scene background
        scene_resource = self.engine.resource_manager.get_resource(scene_id)
        
        if not scene_resource:
            self.logger.warning(f"Scene resource not found: {scene_id}")
            return
        
        # If we need to transition, set up the transition
        if transition and self.current_scene:
            self.current_transition = {
                'type': transition,
                'from': self.current_scene,
                'to': scene_resource,
                'progress': 0,
                'duration': 30  # frames
            }
        else:
            # No transition needed
            self.current_scene = scene_resource
            self.current_transition = None
    
    def render(self, screen: pygame.Surface) -> None:
        """Render the current scene to the screen"""
        if self.current_transition:
            # Handle transitions
            progress = self.current_transition['progress'] / self.current_transition['duration']
            
            if self.current_transition['type'] == 'fade':
                # Fade transition
                if progress < 0.5:
                    # Fading out
                    alpha = 255 * (1 - progress * 2)
                    self._render_with_alpha(screen, self.current_transition['from'], alpha)
                else:
                    # Fading in
                    alpha = 255 * ((progress - 0.5) * 2)
                    self._render_with_alpha(screen, self.current_transition['to'], alpha)
            
            elif self.current_transition['type'] == 'slide_left':
                # Slide left transition
                offset = int(screen.get_width() * progress)
                screen.blit(self.current_transition['from'], (-offset, 0))
                screen.blit(self.current_transition['to'], (screen.get_width() - offset, 0))
            
            # Update transition progress
            self.current_transition['progress'] += 1
            
            # Check if transition is complete
            if self.current_transition['progress'] >= self.current_transition['duration']:
                self.current_scene = self.current_transition['to']
                self.current_transition = None
        
        elif self.current_scene:
            # No transition, just render the current scene
            screen.blit(self.current_scene, (0, 0))
    
    def _render_with_alpha(self, screen: pygame.Surface, image: pygame.Surface, alpha: float) -> None:
        """Render an image with the specified alpha value"""
        alpha = max(0, min(255, int(alpha)))  # Clamp to 0-255
        
        temp = image.copy()
        temp.set_alpha(alpha)
        screen.blit(temp, (0, 0))


class AudioManager:
    """Manages background music and sound effects"""
    
    def __init__(self, engine):
        """Initialize the audio manager"""
        self.engine = engine
        self.current_bgm = None
        self.logger = logging.getLogger("AudioManager")
    
    def play_bgm(self, bgm_id: str, fade_in: float = 0) -> None:
        """Play background music with optional fade-in"""
        # If the requested BGM is already playing, do nothing
        if self.current_bgm == bgm_id:
            return
            
        # Get the music file path
        bgm_path = self.engine.resource_manager.get_resource(bgm_id)
        
        if not bgm_path:
            self.logger.warning(f"BGM resource not found: {bgm_id}")
            return
        
        # Stop any currently playing music
        pygame.mixer.music.stop()
        
        try:
            # Load and play the new music
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.play(-1, fade_ms=int(fade_in * 1000))  # -1 for infinite looping
            self.current_bgm = bgm_id
            self.logger.debug(f"Playing BGM: {bgm_id}")
        except Exception as e:
            self.logger.error(f"Error playing BGM {bgm_id}: {str(e)}")
    
    def stop_bgm(self, fade_out: float = 0) -> None:
        """Stop the currently playing background music with optional fade-out"""
        pygame.mixer.music.fadeout(int(fade_out * 1000))
        self.current_bgm = None
        self.logger.debug("Stopped BGM")
    
    def play_sound(self, sound_id: str) -> None:
        """Play a sound effect"""
        sound = self.engine.resource_manager.get_resource(sound_id)
        
        if not sound:
            self.logger.warning(f"Sound resource not found: {sound_id}")
            return
        
        try:
            sound.play()
            self.logger.debug(f"Playing sound: {sound_id}")
        except Exception as e:
            self.logger.error(f"Error playing sound {sound_id}: {str(e)}")


class GUIManager:
    """Manages the user interface elements"""
    
    def __init__(self, engine):
        """Initialize the GUI manager"""
        self.engine = engine
        self.screen_width, self.screen_height = engine.screen.get_size()
        
        # Text box settings
        self.text_box_rect = pygame.Rect(
            20, 
            self.screen_height - 200, 
            self.screen_width - 40,
            180
        )
        
        # UI elements
        self.font = pygame.font.SysFont(None, 28)
        self.name_font = pygame.font.SysFont(None, 32)
        self.choice_font = pygame.font.SysFont(None, 30)
        
        # Text display state
        self.current_text = ""
        self.displayed_text = ""
        self.text_display_progress = 0
        self.text_speed = 1.0
        self.current_character = None
        
        # Choices
        self.current_choices = []
        self.choice_rects = []
        
        # UI flags
        self.showing_text = False
        self.showing_choices = False
        
        # Notifications
        self.notification = None
        self.notification_timer = 0
        
        self.logger = logging.getLogger("GUIManager")
    
    def show_dialogue(self, text: str, character: str = None, speed: float = 1.0) -> None:
        """Show dialogue text with optional character name"""
        self.current_text = text
        self.displayed_text = ""
        self.text_display_progress = 0
        self.text_speed = speed
        self.current_character = character
        self.showing_text = True
        self.showing_choices = False
    
    def show_choices(self, choices: List[str]) -> None:
        """Show choices for the player to select"""
        self.current_choices = choices
        self.showing_choices = True
        
        # Create rectangles for each choice for hit detection
        self.choice_rects = []
        choice_height = 40
        total_height = len(choices) * (choice_height + 10)
        
        start_y = (self.screen_height - total_height) // 2
        
        for i, choice in enumerate(choices):
            choice_rect = pygame.Rect(
                self.screen_width // 4,
                start_y + i * (choice_height + 10),
                self.screen_width // 2,
                choice_height
            )
            self.choice_rects.append(choice_rect)
    
    def show_notification(self, text: str, duration: int = 60) -> None:
        """Show a temporary notification message"""
        self.notification = text
        self.notification_timer = duration
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle UI-related events, return True if event was handled"""
        # Handle clicks on choices
        if self.showing_choices and event.type == pygame.MOUSEBUTTONDOWN:
            for i, rect in enumerate(self.choice_rects):
                if rect.collidepoint(event.pos):
                    self.engine.story_manager.make_choice(i)
                    self.showing_choices = False
                    return True
        
        # Handle instant text display (clicking during text animation)
        if self.showing_text and not self.showing_choices:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.displayed_text != self.current_text:
                    # Skip to the end of the text
                    self.displayed_text = self.current_text
                    self.text_display_progress = len(self.current_text)
                    return True
        
        return False
    
    def update(self) -> None:
        """Update GUI elements"""
        # Update text display
        if self.showing_text and self.displayed_text != self.current_text:
            self.text_display_progress += self.text_speed
            display_length = min(len(self.current_text), int(self.text_display_progress))
            self.displayed_text = self.current_text[:display_length]
        
        # Update notification timer
        if self.notification:
            self.notification_timer -= 1
            if self.notification_timer <= 0:
                self.notification = None
    
    def render(self, screen: pygame.Surface) -> None:
        """Render GUI elements to the screen"""
        # Update GUI state
        self.update()
        
        # Draw text box
        if self.showing_text:
            # Text box background
            pygame.draw.rect(screen, (0, 0, 0, 180), self.text_box_rect)
            pygame.draw.rect(screen, (255, 255, 255), self.text_box_rect, 2)
            
            # Character name
            if self.current_character:
                name_surface = self.name_font.render(self.current_character, True, (255, 255, 255))
                name_rect = name_surface.get_rect()
                name_rect.topleft = (self.text_box_rect.left + 10, self.text_box_rect.top - name_rect.height - 5)
                
                # Name box background
                name_bg_rect = name_rect.copy()
                name_bg_rect.inflate_ip(20, 10)
                pygame.draw.rect(screen, (0, 0, 0), name_bg_rect)
                pygame.draw.rect(screen, (255, 255, 255), name_bg_rect, 2)
                
                screen.blit(name_surface, name_rect)
            
            # Dialogue text - with simple word wrapping
            words = self.displayed_text.split(' ')
            x, y = self.text_box_rect.left + 20, self.text_box_rect.top + 20
            line_height = self.font.get_height()
            space_width = self.font.size(' ')[0]
            max_width = self.text_box_rect.width - 40
            
            for word in words:
                word_surface = self.font.render(word, True, (255, 255, 255))
                word_width = word_surface.get_width()
                
                if x + word_width > self.text_box_rect.left + max_width:
                    # Move to next line
                    x = self.text_box_rect.left + 20
                    y += line_height
                
                screen.blit(word_surface, (x, y))
                x += word_width + space_width
        
        # Draw choices
        if self.showing_choices:
            for i, (choice, rect) in enumerate(zip(self.current_choices, self.choice_rects)):
                # Choice box background
                pygame.draw.rect(screen, (30, 30, 30), rect)
                pygame.draw.rect(screen, (200, 200, 200), rect, 2)
                
                # Choice text
                choice_surface = self.choice_font.render(choice, True, (255, 255, 255))
                choice_rect = choice_surface.get_rect(center=rect.center)
                screen.blit(choice_surface, choice_rect)
        
        # Draw notification
        if self.notification:
            notification_surface = self.font.render(self.notification, True, (255, 255, 255))
            notification_rect = notification_surface.get_rect(center=(self.screen_width // 2, 50))
            
            # Background
            bg_rect = notification_rect.copy()
            bg_rect.inflate_ip(20, 10)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
            pygame.draw.rect(screen, (255, 255, 255), bg_rect, 2)
            
            screen.blit(notification_surface, notification_rect)


class SaveLoadManager:
    """Handles saving and loading game state"""
    
    def __init__(self, engine):
        """Initialize the save/load manager"""
        self.engine = engine
        self.save_dir = "saves"
        os.makedirs(self.save_dir, exist_ok=True)
        self.logger = logging.getLogger("SaveLoadManager")
    
    def quick_save(self) -> bool:
        """Save the current game state to the quick save slot"""
        return self.save_game("quicksave")
    
    def quick_load(self) -> bool:
        """Load the game state from the quick save slot"""
        return self.load_game("quicksave")
    
    def save_game(self, slot_name: str) -> bool:
        """Save the current game state to the specified slot"""
        try:
            # Create save data
            save_data = {
                'current_node': self.engine.story_manager.current_node,
                'variables': self.engine.game_vars,
                'timestamp': pygame.time.get_ticks(),
                'date': pygame.time.get_ticks()  # In a real game, use a proper timestamp
            }
            
            # Save to file
            save_path = os.path.join(self.save_dir, f"{slot_name}.json")
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2)
                
            self.logger.info(f"Game saved to slot: {slot_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving game: {str(e)}")
            return False
    
    def load_game(self, slot_name: str) -> bool:
        """Load the game state from the specified slot"""
        try:
            # Load from file
            save_path = os.path.join(self.save_dir, f"{slot_name}.json")
            
            if not os.path.exists(save_path):
                self.logger.warning(f"Save slot not found: {slot_name}")
                return False
                
            with open(save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            # Restore game state
            self.engine.story_manager.current_node = save_data['current_node']
            self.engine.game_vars = save_data['variables']
            
            self.logger.info(f"Game loaded from slot: {slot_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading game: {str(e)}")
            return False
    
    def list_saves(self) -> List[Dict[str, Any]]:
        """Get a list of available save slots with metadata"""
        saves = []
        
        for filename in os.listdir(self.save_dir):
            if filename.endswith('.json'):
                try:
                    save_path = os.path.join(self.save_dir, filename)
                    with open(save_path, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                        
                    slot_name = os.path.splitext(filename)[0]
                    saves.append({
                        'slot': slot_name,
                        'timestamp': save_data.get('timestamp', 0),
                        'date': save_data.get('date', 'Unknown')
                    })
                except Exception as e:
                    self.logger.error(f"Error reading save file {filename}: {str(e)}")
        
        return saves


if __name__ == "__main__":
    # Example usage
    engine = VNEngine(resolution=(1280, 720), title="My Visual Novel")
    
    # In a real app, you'd load a script file here
    # engine.load_game("resources/scripts/main.json")
    
    # For demo purposes, just run the engine
    # engine.run()