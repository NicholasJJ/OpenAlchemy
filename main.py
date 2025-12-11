import os
import json
from recipe import Recipe
import recipe

import asyncio
from nicegui import ui
from nicegui.events import MouseEventArguments

from material import Material

# Create Basic Materials:
water = Material(name="WATER", emoji="💧")
fire = Material(name="FIRE", emoji="🔥")
earth = Material(name="EARTH", emoji="🪱")
air = Material(name="AIR", emoji="💨")
dna = Material(name="DNA", emoji="🧬")

discovered_materials = [water, fire, earth, air, dna]
canvas_widgets = []  # Track widgets on the canvas

script_dir = os.path.dirname(__file__)
filename = "recipes.json"

def initDiscoveredMaterials():
    with open(os.path.join(script_dir, filename), 'r') as file:
        data = json.load(file)
        recipes = [Recipe(r["material_list"], Material(**r["output"])) for r in data]

    # Init discovered materials
    for recipe in recipes:
        if recipe.output not in discovered_materials:
            discovered_materials.append(recipe.output)

def clearRecipes(ui_list):
    recipe.clearRecipes()
    discovered_materials.clear()
    discovered_materials.extend([water, fire, earth, air, dna])
    updateDiscoveredMaterialsList(ui_list)
    # Clear canvas widgets
    for widget in canvas_widgets[:]:
        widget['card'].delete()
        canvas_widgets.remove(widget)

def updateDiscoveredMaterialsList(ui_list):
    ui_list.clear()
    for material in discovered_materials:
        with ui_list:
            item = ui.item().classes('bg-white rounded-lg shadow-md cursor-pointer hover:bg-gray-50')
            item.on_click(lambda m=material: addToCanvas(m))
            with item:
                with ui.item_section():
                    ui.item_label(f"{material.emoji} {material.name}")

def addToCanvas(material):
    """Add a material widget to the canvas"""
    # Create a draggable card on the canvas
    # Random position within canvas bounds (800x500, with 100px card width/height and some margin)
    import random
    random_x = random.randint(50, 700)
    random_y = random.randint(50, 400)
    
    with canvas_container:
        card = ui.card().classes('absolute cursor-move bg-white rounded-lg shadow-lg p-4 hover:shadow-xl transition-shadow')
        card.style(f'left: {random_x}px; top: {random_y}px; width: 100px; text-align: center;')
        
        widget_data = {
            'material': material,
            'card': card,
            'x': random_x,
            'y': random_y,
            'dragging': False,
            'offset_x': 0,
            'offset_y': 0
        }
        
        with card:
            ui.label(material.emoji).classes('text-4xl')
            ui.label(material.name).classes('text-xs font-bold')
        
        # Make it draggable - stop event propagation
        card.on('mousedown', lambda e, w=widget_data: start_drag(e, w), ['.stop'])
        
        canvas_widgets.append(widget_data)
    
    ui.notify(f"Added {material.emoji} {material.name} to canvas!")

def start_drag(e: MouseEventArguments, widget):
    """Start dragging a widget"""
    widget['dragging'] = True
    # Center the widget under the mouse (widget is 100px wide, so offset by 50px)
    widget['offset_x'] = 50
    widget['offset_y'] = 50
    # Disable pointer events on ALL cards so they don't interfere with mouse tracking
    # Also set z-index: reset non-dragging cards to normal, raise the dragging card
    for w in canvas_widgets:
        if w is widget:
            w['card'].style(f'left: {w["x"]}px; top: {w["y"]}px; width: 100px; text-align: center; pointer-events: none; z-index: 1000;')
        else:
            w['card'].style(f'left: {w["x"]}px; top: {w["y"]}px; width: 100px; text-align: center; pointer-events: none; z-index: 1;')

async def on_mouse_move(e: MouseEventArguments):
    """Handle mouse movement for dragging"""
    for widget in canvas_widgets:
        if widget.get('dragging'):
            # Use offsetX/Y which is always relative to the canvas container
            canvas_mouse_x = e.args['offsetX']
            canvas_mouse_y = e.args['offsetY']
            
            # Calculate new position (mouse position minus the offset to keep widget under cursor)
            new_x = canvas_mouse_x - widget['offset_x']
            new_y = canvas_mouse_y - widget['offset_y']
            
            # Check for potential collision with other widgets
            collision_detected = False
            for other in canvas_widgets:
                if other is not widget:
                    dx = new_x - other['x']
                    dy = new_y - other['y']
                    distance = (dx * dx + dy * dy) ** 0.5
                    
                    if distance < 80:  # Collision threshold
                        collision_detected = True
                        # Add wiggle animation to both widgets
                        other['card'].classes(remove='wiggle')
                        other['card'].classes(add='wiggle')
                        break
            
            # Remove wiggle from all non-colliding widgets
            if not collision_detected:
                for other in canvas_widgets:
                    if other is not widget:
                        other['card'].classes(remove='wiggle')
            
            # Update position (keep pointer-events: none during drag)
            widget['x'] = new_x
            widget['y'] = new_y
            widget['card'].style(f'left: {new_x}px; top: {new_y}px; width: 100px; text-align: center; pointer-events: none;')

async def on_mouse_up(e: MouseEventArguments):
    """Handle mouse release - check for collisions and combine materials"""
    for widget in canvas_widgets:
        if widget.get('dragging'):
            widget['dragging'] = False
            # Re-enable pointer events on ALL widgets so they can be dragged again
            for w in canvas_widgets:
                w['card'].style(f'left: {w["x"]}px; top: {w["y"]}px; width: 100px; text-align: center; pointer-events: auto;')
            
            # Check for collision with other widgets
            for other in canvas_widgets:
                if other is not widget:
                    # Simple bounding box collision detection
                    dx = widget['x'] - other['x']
                    dy = widget['y'] - other['y']
                    distance = (dx * dx + dy * dy) ** 0.5
                    
                    if distance < 80:  # Collision threshold
                        # Combine materials
                        await combine_materials(widget, other)
                        return

async def combine_materials(widget1, widget2):
    """Combine two materials and create a new one"""
    mat1 = widget1['material']
    mat2 = widget2['material']
    
    ui.notify(f"Combining {mat1.emoji} {mat1.name} + {mat2.emoji} {mat2.name}...", type='info')
    
    # Check if recipe already exists
    with open(os.path.join(script_dir, filename), 'r') as file:
        data = json.load(file)
        recipes = [Recipe(r["material_list"], Material(**r["output"])) for r in data]
    
    existing_material = None
    for m_recipe in recipes:
        if mat1.name.upper() in m_recipe.material_list and mat2.name.upper() in m_recipe.material_list:
            existing_material = m_recipe.output
            ui.notify(f"Creating {existing_material.emoji} {existing_material.name}!", type='info')
            break
    
    # If recipe exists, use the existing material, otherwise create new
    if existing_material:
        new_material = existing_material
    else:
        await asyncio.sleep(0.1)  # Let UI update
        new_material = recipe.createRecipe(mat1.name.upper(), mat2.name.upper())
        if new_material not in discovered_materials:
            discovered_materials.append(new_material)
    
    # Remove both widgets from canvas
    widget1['card'].delete()
    widget2['card'].delete()
    canvas_widgets.remove(widget1)
    canvas_widgets.remove(widget2)
    
    # Add new material widget at the collision point
    with canvas_container:
        card = ui.card().classes('absolute cursor-move bg-white rounded-lg shadow-lg p-4 hover:shadow-xl transition-shadow')
        card.style(f'left: {widget2["x"]}px; top: {widget2["y"]}px; width: 100px; text-align: center;')
        
        widget_data = {
            'material': new_material,
            'card': card,
            'x': widget2['x'],
            'y': widget2['y'],
            'dragging': False
        }
        
        with card:
            ui.label(new_material.emoji).classes('text-4xl')
            ui.label(new_material.name).classes('text-xs font-bold')
        
        card.on('mousedown', lambda e, w=widget_data: start_drag(e, w))
        canvas_widgets.append(widget_data)
    
    ui.notify(f"✨ Discovered {new_material.emoji} {new_material.name}!", type='positive')
    updateDiscoveredMaterialsList(discoveredMaterials_list)

# Initialize and build UI
initDiscoveredMaterials()
ui.query('body').style('font-family: monospace;')

# Add wiggle animation CSS and prevent text selection
ui.add_head_html('''
<style>
@keyframes wiggle {
    0%, 100% { transform: rotate(0deg); }
    25% { transform: rotate(-3deg) scale(1.05); }
    75% { transform: rotate(3deg) scale(1.05); }
}
.wiggle {
    animation: wiggle 0.3s ease-in-out infinite;
}
/* Prevent text selection on cards */
.q-card {
    user-select: none;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
}
</style>
''')

ui.header().classes('bg-transparent')
with ui.column().classes('w-full items-center'):
    ui.label("Open Source Alchemy 🧪").style('color: black; font-size: 200%').classes('justify-center')

with ui.row().classes('justify-center w-full gap-4 p-4'):
    # Left side: Materials palette
    with ui.column().classes('items-center gap-2'):
        ui.label("Materials").classes('text-xl font-bold')
        discoveredMaterials_list = ui.scroll_area().classes('bg-neutral-100 rounded-lg shadow-md h-[500px] w-[200px] p-2')
        reset_button = ui.button('Reset 🔄️', color='red', on_click=lambda: clearRecipes(discoveredMaterials_list))
        reset_button.classes('rounded-lg w-full')
        reset_button.tooltip('Reset discovered materials')
    
    # Right side: Canvas area
    with ui.column().classes('items-center gap-2'):
        ui.label("Canvas - Drag materials here to combine!").classes('text-xl font-bold')
        canvas_container = ui.element('div').classes('relative bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg shadow-lg')
        canvas_container.style('width: 800px; height: 500px; border: 2px dashed #cbd5e0;')
        
        # Add mouse event handlers to the canvas
        canvas_container.on('mousemove', on_mouse_move)
        canvas_container.on('mouseup', on_mouse_up)
        canvas_container.on('mouseleave', on_mouse_up)  # Stop dragging if mouse leaves canvas

updateDiscoveredMaterialsList(discoveredMaterials_list)

ui.run()
