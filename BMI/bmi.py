import tkinter as tk
from tkinter import messagebox, filedialog
import math
import json
import os
from datetime import datetime
from tkinter import ttk
import threading # Required for simulating non-blocking API calls
import time # Used for simulating API delay
import urllib.parse # Used for safely encoding queries in click tags

# --- TOOLTIP CLASS (Unchanged) ---
class Tooltip:
    """Creates a tooltip that displays text when hovering over a widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = 0
        self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self, event=None):
        if self.tip_window or not self.text:
            return

        # Get coordinates to display the tooltip slightly below and right of the widget
        self.x = self.widget.winfo_rootx() + 20
        self.y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{self.x}+{self.y}")

        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Helvetica", "8", "normal")) # Changed font
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

# --- GLOBAL STYLES & CONFIGURATION (Updated Font to Helvetica) ---
class Style:
    # Color Palette (Soft, Calming, Modern)
    BG_PRIMARY = '#F0F8FF' # Alice Blue (Soft Background)
    BG_CARD = 'white'
    BG_NAV = '#E0F7FA' # Light Cyan (Navigation Bar)
    COLOR_ACCENT_GREEN = '#4CAF50' # Green for Good/Plan
    COLOR_ACCENT_BLUE = '#1E90FF' # Dodger Blue for History/Goals
    COLOR_DANGER = '#FF4500' # OrangeRed for Alerts
    COLOR_WARNING = '#FFD700' # Gold for Overweight
    COLOR_NAV_TEXT = '#333333'
    COLOR_BUTTON_HOVER = '#3e8e41'
    COLOR_WATER = '#81D4FA' # Light Blue for Hydration

    # Fonts (Switched to Helvetica and adjusted sizes for impact)
    FONT_HEADING = ('Helvetica', 20, 'bold')
    FONT_NAV = ('Helvetica', 12, 'bold')
    FONT_LABEL = ('Helvetica', 10)
    FONT_INPUT = ('Helvetica', 12)
    FONT_RESULT_VALUE = ('Helvetica', 24, 'bold')
    FONT_CATEGORY = ('Helvetica', 15, 'bold')
    FONT_TOOLTIP = ('Helvetica', 9)

    # Chat Styles
    CHAT_BOT_BG = '#E8F5E9' # Light Greenish for Bot Bubble
    CHAT_USER_BG = '#DDEEFF' # Light Blue for User Bubble

class BMICalculatorApp:
    """
    A graphical BMI Calculator application using Tkinter with a multi-view interface,
    allowing users to switch between the Calculator, Health Planner, and Chatbot sections.
    """

    # API Key Placeholder (for demonstration)
    GEMINI_API_KEY = "AIzaSyAdR41ni44KSALJLOE75qFqhoCQtu3ltKg"

    # Constants for BMI categories
    BMI_MIN_NORMAL = 18.5
    BMI_MAX_NORMAL = 24.9
    BMI_EXTREME_LOW = 16.0
    BMI_EXTREME_HIGH = 35.0
    HISTORY_FILE = 'bmi_history.json'
    WATER_GOAL_ML = 2500 # Default daily water goal

    ACTIVITY_MULTIPLIERS = {
        "Sedentary": 1.2, "Lightly Active": 1.375, "Moderately Active": 1.55,
        "Very Active": 1.725, "Extra Active": 1.9,
    }
    ACTIVITY_OPTIONS = list(ACTIVITY_MULTIPLIERS.keys())
    ACTIVITY_EXPLANATIONS = {
        "Sedentary": "Little or no exercise (desk job, reading).",
        "Lightly Active": "Light exercise/sports 1-3 days/week.",
        "Moderately Active": "Moderate exercise/sports 3-5 days/week (most gym-goers).",
        "Very Active": "Hard exercise/sports 6-7 days/week.",
        "Extra Active": "Very hard exercise/physical job or 2x/day training."
    }

    DIET_OPTIONS = ["Omnivore", "Vegetarian", "Vegan"]

    def __init__(self, master):
        self.master = master
        master.title("Advanced BMI & Health Planner")
        master.geometry("800x700")
        master.resizable(True, True)
        master.configure(bg=Style.BG_PRIMARY)

        # --- State Variables ---
        self.unit_system = tk.StringVar(value="metric")
        self.gender = tk.StringVar(value="Male")
        self.activity_level = tk.StringVar(value=self.ACTIVITY_OPTIONS[2])
        self.health_goal = tk.StringVar(value="Maintain Weight")
        self.goal_options = ["Lose Weight", "Maintain Weight", "Gain Muscle"]
        self.diet_preference = tk.StringVar(value=self.DIET_OPTIONS[0])
        self.active_frame = tk.StringVar(value='Calculator')

        self.water_intake_ml = tk.IntVar(value=0)
        self.water_add_ml = tk.StringVar(value="250")
        self.chatbot_is_loading = False # Loading state for API

        self.weight_label_text = tk.StringVar(value="Weight (kg):")
        self.height_label_text = tk.StringVar(value="Height (m):")
        self.current_inputs = {}
        self.history = []

        # Chatbot specific variables (IMPROVEMENT: Structured History)
        self.chatbot_input = None
        self.chatbot_display = None
        self.chat_history = [] # Stores structured chat history (role/text pairs)
        self.initial_message_sent = False # Flag to manage the first greeting

        # Initialize widgets to None for safety checks
        self.water_bar = None
        self.water_status_label = None
        self.chatbot_loading_label = None

        # --- Main Layout Frames (Side-by-Side) ---
        self.main_container = tk.Frame(master, bg=Style.BG_PRIMARY)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Navbar Frame (Left)
        self.navbar_frame = tk.Frame(self.main_container, width=180, bg=Style.BG_NAV, relief=tk.RAISED, bd=1)
        self.navbar_frame.pack(side=tk.LEFT, fill=tk.Y)

        # 2. Content Frame (Right)
        self.content_container = tk.Frame(self.main_container, bg=Style.BG_PRIMARY)
        self.content_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Dictionary to hold the dynamic frames
        self.frames = {}

        # --- Setup UI Sections ---
        self.setup_navbar()
        self.setup_planner_frame()
        self.setup_chatbot_frame()
        self.setup_calculator_frame()

        # Initial View
        self.load_history()
        self.show_frame('Calculator')

    # --- NAV BAR LOGIC ---

    def setup_navbar(self):
        """Creates the side navigation bar with buttons to switch views."""
        tk.Label(self.navbar_frame, text="Health Dashboard", font=Style.FONT_HEADING, bg=Style.BG_NAV, fg=Style.COLOR_NAV_TEXT).pack(pady=(20, 30), padx=5)

        self.nav_buttons = {}

        # Button Styles
        nav_btn_style = {'font': Style.FONT_NAV, 'width': 18, 'pady': 10, 'relief': tk.FLAT, 'bd': 0,
                         'bg': Style.BG_NAV, 'fg': Style.COLOR_NAV_TEXT, 'activebackground': '#A9DCE6'}

        # BMI Calculator Button
        self.nav_buttons['Calculator'] = tk.Button(self.navbar_frame, text="📊 BMI Calculator",
                                                     command=lambda: self.show_frame('Calculator'), **nav_btn_style)
        self.nav_buttons['Calculator'].pack(pady=5, padx=10, fill=tk.X)

        # Health Planner Button
        self.nav_buttons['Planner'] = tk.Button(self.navbar_frame, text="🗓️ Health Planner",
                                               command=lambda: self.view_plan(), **nav_btn_style)
        self.nav_buttons['Planner'].pack(pady=5, padx=10, fill=tk.X)

        # Smart Health Chatbot Button
        self.nav_buttons['Chatbot'] = tk.Button(self.navbar_frame, text="🤖 Smart Health Chatbot",
                                                command=lambda: self.show_frame('Chatbot'), **nav_btn_style)
        self.nav_buttons['Chatbot'].pack(pady=5, padx=10, fill=tk.X)

    def show_frame(self, page_name):
        """Switches the currently visible frame and updates the navbar highlight."""

        # Change button styling
        for name, button in self.nav_buttons.items():
            if name == page_name:
                button.config(bg=Style.COLOR_ACCENT_BLUE, fg='white')
                self.active_frame.set(page_name)
            else:
                button.config(bg=Style.BG_NAV, fg=Style.COLOR_NAV_TEXT)

        # Raise the selected frame
        frame = self.frames[page_name]
        frame.tkraise()

        # Bind Return key only to the active frame's primary action
        if page_name == 'Calculator':
            self.master.bind('<Return>', lambda event: self.calculate_bmi_gui())
        elif page_name == 'Chatbot' and self.chatbot_input:
            self.master.bind('<Return>', lambda event: self.send_message())
            self.chatbot_input.focus_set() # Focus the input field
            
            # IMPROVEMENT: Use dedicated interactive message on first open
            if not self.initial_message_sent:
                self.insert_initial_suggestions()
                self.initial_message_sent = True
        else:
            self.master.unbind('<Return>')


    # --- CHATBOT VIEW SETUP ---
    def setup_chatbot_frame(self):
        chatbot_frame = tk.Frame(self.content_container, bg=Style.BG_PRIMARY)
        self.frames['Chatbot'] = chatbot_frame
        chatbot_frame.grid(row=0, column=0, sticky='nsew')
        chatbot_frame.grid_columnconfigure(0, weight=1)
        chatbot_frame.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = tk.Frame(chatbot_frame, bg=Style.BG_CARD, padx=10, pady=10, relief=tk.GROOVE)
        header_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        tk.Label(header_frame, text="🤖 Smart Health Chatbot", font=Style.FONT_HEADING, bg=Style.BG_CARD, fg=Style.COLOR_ACCENT_BLUE).pack(side=tk.LEFT)

        # Chat Display Area
        chat_display_frame = tk.Frame(chatbot_frame, bg=Style.BG_CARD, bd=1, relief=tk.GROOVE)
        chat_display_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 10))

        # Changed font in Text widget
        self.chatbot_display = tk.Text(chat_display_frame, wrap=tk.WORD, state=tk.DISABLED, font=('Helvetica', 10), bg='#F5F5F5', bd=0, padx=10, pady=10)

        scrollbar = tk.Scrollbar(chat_display_frame, command=self.chatbot_display.yview)
        self.chatbot_display['yscrollcommand'] = scrollbar.set

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chatbot_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tags for styling message bubbles
        # User message: Light blue background, aligned right
        self.chatbot_display.tag_config('user', background=Style.CHAT_USER_BG, foreground='#333333', spacing1=7, spacing3=7, lmargin1=250, lmargin2=10)
        # Bot message: Light green background, aligned left
        self.chatbot_display.tag_config('bot', background=Style.CHAT_BOT_BG, foreground='#1E90FF', spacing1=7, spacing3=7, rmargin=250)
        
        # New tag for clickable suggestions (styled like a link)
        self.chatbot_display.tag_config('suggestion_link', foreground=Style.COLOR_ACCENT_BLUE, underline=1, font=('Helvetica', 10, 'bold'))
        # Bind the click event to the tag
        self.chatbot_display.tag_bind('suggestion_link', '<Button-1>', self.on_suggestion_click)
        
        self.chatbot_display.tag_config('loading', foreground='#FF4500', justify='center')

        # Control Buttons Frame
        control_frame = tk.Frame(chatbot_frame, bg=Style.BG_PRIMARY)
        control_frame.grid(row=2, column=0, sticky='ew', pady=(5, 5))
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(2, weight=1)

        # Loading Indicator
        self.chatbot_loading_label = tk.Label(control_frame, text="", font=('Helvetica', 10, 'bold'), fg=Style.COLOR_DANGER, bg=Style.BG_PRIMARY)
        self.chatbot_loading_label.grid(row=0, column=0, sticky='w', padx=10)

        # Clear and Save Buttons
        tk.Button(control_frame, text="🧹 Clear Chat", command=self.clear_chatbot_history,
                  bg='#CCCCCC', fg='#555555', font=('Helvetica', 10), relief=tk.RAISED, bd=2).grid(row=0, column=1, sticky='e', padx=5)

        tk.Button(control_frame, text="💾 Save History", command=self.save_chatbot_history,
                  bg=Style.COLOR_ACCENT_BLUE, fg='white', font=('Helvetica', 10), relief=tk.RAISED, bd=2).grid(row=0, column=2, sticky='e')

        # Input and Send Button Frame
        input_frame = tk.Frame(chatbot_frame, bg=Style.BG_PRIMARY)
        input_frame.grid(row=3, column=0, sticky='ew', pady=(5, 0))
        input_frame.grid_columnconfigure(0, weight=1)

        self.chatbot_input = tk.Entry(input_frame, font=Style.FONT_INPUT, relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor=Style.COLOR_ACCENT_BLUE, bg='#FFFFFF')
        self.chatbot_input.grid(row=0, column=0, sticky='ew', padx=(0, 10), ipady=4)

        send_button = tk.Button(input_frame, text="Send", command=self.send_message,
                                 bg=Style.COLOR_ACCENT_GREEN, fg='white', font=('Helvetica', 11, 'bold'),
                                 relief=tk.RAISED, padx=15, pady=5, activebackground=Style.COLOR_BUTTON_HOVER, bd=2)
        send_button.grid(row=0, column=1, sticky='e')

    def on_suggestion_click(self, event):
        """Handles clicks on the suggestion links in the chat display."""
        try:
            # Determine the index of the character clicked
            index = self.chatbot_display.index(f"@{event.x},{event.y}")
            # Get all tags at that index
            tags = self.chatbot_display.tag_names(index)

            # Look for a tag that starts with 'query_' which holds the actual command
            for tag in tags:
                if tag.startswith("query_"):
                    # The actual query is URL-encoded/escaped in the tag name
                    query = urllib.parse.unquote_plus(tag.split("query_")[1])
                    
                    # Simulate user typing and sending the message
                    self.chatbot_input.delete(0, tk.END)
                    self.chatbot_input.insert(0, query)
                    self.send_message()
                    return
        except Exception:
            # Fail silently if not a clickable link
            pass

    def insert_initial_suggestions(self):
        """Inserts the initial welcome message with clickable suggestions."""
        
        # 1. Base Welcome Message
        welcome_text = "Hello! I'm your Smart Health Assistant. I can analyze your metrics. **Remember, I am not a doctor.**\n\n"
        
        self.chatbot_display.config(state=tk.NORMAL)
        self.chatbot_display.insert(tk.END, "Bot: " + welcome_text.replace('**',''), 'bot')
        
        # 2. Suggestions list
        suggestions = [
            ("Water Status", "what is my water status"),
            ("View My Plan", "tell me about my plan"),
            ("My Health Report", "my health report"),
            ("Medical Disclaimer", "what is the medical disclaimer"),
            ("Cardio Health Risks", "what are the risks of high blood pressure?"),
        ]
        
        self.chatbot_display.insert(tk.END, "Bot: Quick Links (Click to ask):\n", 'bot')
        
        for display_text, query in suggestions:
            # URL-encode the query to safely embed it in the tag name
            encoded_query = urllib.parse.quote_plus(query)
            dynamic_tag = f"query_{encoded_query}"
            
            # Ensure the dynamic tag is defined (it is defined to inherit 'suggestion_link' style/binding)
            self.chatbot_display.tag_config(dynamic_tag, 
                                            foreground=Style.COLOR_ACCENT_BLUE, 
                                            underline=1, 
                                            font=('Helvetica', 10, 'bold'))
            
            # Insert the clickable text and apply two tags
            self.chatbot_display.insert(tk.END, f"  [ {display_text} ]  ", ('suggestion_link', dynamic_tag))
            self.chatbot_display.insert(tk.END, " \n", 'bot')
            
        self.chatbot_display.insert(tk.END, "\n", 'bot')
        
        # Re-enable the text widget and autoscroll
        self.chatbot_display.config(state=tk.DISABLED)
        self.chatbot_display.see(tk.END) # Auto-scroll


    def clear_chatbot_history(self):
        """Clears the displayed chat history and internal history."""
        self.chat_history = []
        self.initial_message_sent = False # Allow re-sending the greeting
        self.chatbot_display.config(state=tk.NORMAL)
        self.chatbot_display.delete('1.0', tk.END)
        self.chatbot_display.config(state=tk.DISABLED)

        # Re-send the initial message after clearing
        self.show_frame('Chatbot') # This will trigger the initial message send

    def save_chatbot_history(self):
        """Exports the conversation history to a text file using structured history."""
        try:
            if not self.chat_history:
                messagebox.showinfo("Save Chat", "The chat history is empty.")
                return

            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Chat History"
            )

            if file_path:
                formatted_conversation = ""
                for message in self.chat_history:
                    role = "[USER]" if message['role'] == 'user' else "[BOT]"
                    formatted_conversation += f"{role}: {message['text'].strip()}\n\n"

                with open(file_path, 'w') as f:
                    f.write(f"Health Chatbot Conversation History ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n")
                    f.write("----------------------------------------------------------------\n\n")
                    f.write(formatted_conversation.strip())

                messagebox.showinfo("Export Successful", f"Chat history saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save file: {e}")

    def display_chatbot_message(self, message, is_user):
        """Adds a message to the chat display area and auto-scrolls."""
        tag = 'user' if is_user else 'bot'
        prefix = "User: " if is_user else "Bot: "

        self.chatbot_display.config(state=tk.NORMAL)
        self.chatbot_display.insert(tk.END, prefix + message + '\n', tag)
        self.chatbot_display.config(state=tk.DISABLED)
        self.chatbot_display.see(tk.END) # Auto-scroll


    def set_loading_state(self, is_loading):
        """Enables/disables loading state UI elements."""
        self.chatbot_is_loading = is_loading
        if is_loading:
            self.chatbot_loading_label.config(text="... Thinking ...", fg=Style.COLOR_DANGER)
            self.chatbot_input.config(state=tk.DISABLED)
        else:
            self.chatbot_loading_label.config(text="")
            self.chatbot_input.config(state=tk.NORMAL)

    def get_personalized_health_report(self):
        """Gathers all current health metrics and settings into a single string for chatbot context."""
        if not self.current_inputs:
            return "No recent health metrics are available. Please calculate your BMI first."

        data = self.current_inputs

        # Standardize weight/height for display in the report (using the raw units from input)
        if data['unit'] == 'imperial':
            weight_str = f"{data['weight']} lbs"
            height_inches = data['height']
            feet = int(height_inches // 12)
            inches = round(height_inches % 12)
            height_str = f"{feet} ft {inches} in"
        else:
            weight_str = f"{data['weight']} kg"
            height_str = f"{data['height']} m"

        report = (
            f"--- User Health Snapshot ---\n"
            f"BMI: {data.get('bmi', 'N/A'):.2f} ({data.get('category', 'N/A')})\n"
            f"Goal: {data.get('goal', 'N/A')}\n"
            f"Activity: {data.get('activity', 'N/A')}\n"
            f"Diet: {data.get('diet', 'N/A')}\n"
            f"Age/Gender: {data.get('age', 'N/A')} / {data.get('gender', 'N/A')}\n"
            f"Weight/Height: {weight_str} / {height_str}\n"
            f"Water Intake Today: {self.water_intake_ml.get()}ml\n"
            f"--------------------------\n"
        )
        return report

    def simulate_api_call(self, query):
        """
        SIMULATION of an asynchronous API call to an LLM (like Gemini).
        """
        time.sleep(1.5) # Simulate network delay
        return self.get_rule_based_response(query)


    def get_rule_based_response(self, query):
        """Enhanced rule-based responses for common health queries (Fallback/Simulation)
           including dynamic state reporting and medical disclaimers."""
        q = query.lower()

        # IMPORTANT: Medical Disclaimer that must be prepended to any sensitive answer
        MEDICAL_DISCLAIMER = "⚠️ Disclaimer: I am an AI assistant, not a doctor. **Always consult a qualified healthcare professional** for medical diagnosis or treatment."

        # 1. Dynamic Water Status Query
        if "water status" in q or "my water" in q or "hydration" in q or "how much water" in q:
            current = self.water_intake_ml.get()
            goal = self.WATER_GOAL_ML

            if current >= goal:
                status = f"Fantastic! You've logged **{current}ml** which meets your daily goal of **{goal}ml**! Stay consistent. You're doing great!"
            else:
                remaining = goal - current
                status = f"You've logged **{current}ml** so far against a goal of **{goal}ml**. That means you need about **{remaining}ml** more today. Keep sipping!"
            return status

        # 2. Dynamic Diet/Plan Query
        if "diet plan" in q or "my goals" in q or "my plan" in q:
            if not self.current_inputs:
                return "I need your personal metrics first! Please go to the 'BMI Calculator' tab, calculate your BMI, and then check the 'Health Planner' tab. Once that's done, I can give you personalized advice!"

            goal = self.current_inputs.get("goal", "Maintain Weight")
            diet = self.current_inputs.get("diet", "Omnivore")

            # Advice based on goal and diet preference
            if goal == "Lose Weight":
                advice = f"Your current goal is **Weight Loss**. Focus on a calorie deficit and high-volume, satiating foods. With your **{diet}** preference, ensure plenty of lean protein and fiber to manage hunger and preserve muscle."
            elif goal == "Gain Muscle":
                advice = f"Your current goal is **Muscle Gain**. Focus on a slight calorie surplus and prioritize high-quality protein (aim for ~1.6g per kg of body weight). Make sure your **{diet}** choice supports enough protein."
            else:
                advice = f"Your current goal is to **Maintain Weight**. The key is balance and consistency. Continue following a diverse **{diet}** diet and keeping up your current activity level."

            return f"Based on your latest inputs:\n- Health Goal: **{goal}**\n- Diet Preference: **{diet}**\n\n{advice}"

        # 3. Dynamic Health Report (IMPROVEMENT)
        if "my health report" in q or "my metrics" in q:
            report = self.get_personalized_health_report()
            return f"Here is your latest summary:\n{report}"

        # 4. Medical/Sensitive Queries (IMPROVEMENT: New medical suggestions)
        if "what is the medical disclaimer" in q:
            return MEDICAL_DISCLAIMER + "\n\nI repeat this for all sensitive health queries. Your safety is paramount. How else can I assist with general health information?"

        if "medication" in q or "drug" in q or "supplements" in q:
            return f"{MEDICAL_DISCLAIMER}\n\nI can suggest general benefits of common vitamins, but for advice regarding specific **medication or supplements**, you must speak with your pharmacist or prescribing doctor. Do you want to know about general health benefits of Vitamin D?"

        if "diabetes" in q or "blood sugar" in q:
            return f"{MEDICAL_DISCLAIMER}\n\nManaging blood sugar requires a personalized approach. General tips include: prioritizing low-glycemic index foods, daily moderate exercise, and consistent meal timings. Speak to a doctor or dietitian for a custom plan."

        if "heart disease" in q or "cardio" in q or "blood pressure" in q:
             return f"{MEDICAL_DISCLAIMER}\n\nTo promote cardiovascular health, focus on a diet low in sodium and saturated fats (like the DASH diet), engage in regular aerobic exercise, and quit smoking. If you have high blood pressure, consult your physician immediately."
        
        if "allergies" in q or "intolerance" in q:
             return f"{MEDICAL_DISCLAIMER}\n\nIf you suspect food allergies or intolerances, you should consult an allergist. In the meantime, strict avoidance of suspected triggers is necessary. Make sure to communicate your {self.diet_preference.get()} diet preference to me for safe meal suggestions."

        # 5. Existing general queries
        if "healthy bmi" in q or "what is bmi" in q:
            return "A healthy BMI range is typically **18.5 to 24.9**. While BMI is a quick screening tool, it's essential to consider muscle mass and body fat percentage for a complete picture. Do you want to know the ideal weight range for your height?"

        if "foods" in q and ("weight loss" in q or "lose weight" in q):
            return "To achieve sustainable weight loss, prioritize **whole, unprocessed foods**. Focus on lean proteins (like chicken, beans, and fish), high-fiber vegetables, and whole grains. Avoid liquid calories and excessive sugar."

        if "exercise" in q or "workout" in q:
            return "For general health, the CDC recommends at least 150 minutes of moderate-intensity activity (e.g., brisk walking) per week, plus muscle-strengthening activities two days a week. We can help you integrate that into your Planner!"

        if "balanced diet" in q:
            return "A truly balanced diet requires hitting your **macro-nutrient targets** (protein, carbs, fats) while consuming a wide variety of **micronutrients** (vitamins, minerals). Aim for a colorful plate to ensure diversity."

        if "hello" in q or "hi" in q:
            return "Hello! I'm your Smart Health Assistant, powered by AI. I can answer your wellness questions, but remember I am not a doctor. What health topic can I assist with?"

        return "I'm generating an informed response for your query. As an AI assistant, I can provide general health information, but please consult a healthcare professional for specific medical advice."

    def send_message(self):
        user_query = self.chatbot_input.get().strip()
        if not user_query or self.chatbot_is_loading:
            return

        # Add user message to display and history
        self.display_chatbot_message(user_query, is_user=True)
        self.chat_history.append({'role': 'user', 'text': user_query})
        self.chatbot_input.delete(0, tk.END)
        self.set_loading_state(True)

        # Pass the query to the handler
        thread = threading.Thread(target=self.handle_api_response, args=(user_query,))
        thread.start()


    def handle_api_response(self, query):
        """Called by the thread to handle the simulated API call and update the GUI."""

        bot_response = self.simulate_api_call(query)

        # Use master.after to safely update the GUI from the thread
        self.master.after(0, lambda: [
            self.set_loading_state(False),
            self.display_chatbot_message(bot_response, is_user=False),
            self.chat_history.append({'role': 'bot', 'text': bot_response})
        ])

    # --- CALCULATOR VIEW SETUP (Inputs & Results) ---

    def setup_calculator_frame(self):
        """Builds the entire input and result UI, made scrollable."""
        calculator_frame = tk.Frame(self.content_container, bg=Style.BG_PRIMARY)
        self.frames['Calculator'] = calculator_frame
        calculator_frame.grid(row=0, column=0, sticky='nsew')

        # Ensure the frame expands within the container
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        # Setup Scrollable Canvas within the Calculator Frame
        scroll_canvas = tk.Canvas(calculator_frame, bg=Style.BG_PRIMARY, bd=0, highlightthickness=0)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(calculator_frame, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        # Main frame inside the scrollable canvas.
        main_frame = tk.Frame(scroll_canvas, bg=Style.BG_PRIMARY, padx=10, pady=10)
        scroll_canvas.create_window((0, 0), window=main_frame, anchor="nw", width=550)

        # Configuration to make scrolling work when window resizes
        def on_frame_configure(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def on_canvas_resize(event):
            canvas_width = event.width
            scroll_canvas.itemconfig(self.window_id, width=canvas_width)

        main_frame.bind("<Configure>", on_frame_configure)
        scroll_canvas.bind('<Configure>', on_canvas_resize)
        self.window_id = scroll_canvas.create_window((0, 0), window=main_frame, anchor="nw", width=scroll_canvas.winfo_width())

        main_frame.grid_columnconfigure(1, weight=1)

        # --- UI Elements ---
        tk.Label(main_frame, text="Personal Metrics Input", font=Style.FONT_HEADING, bg=Style.BG_PRIMARY, fg='#333').grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky='w')

        # --- Dynamic Feedback Label ---
        self.dynamic_feedback_label = tk.Label(main_frame, text="💡 Enter your details to get started!",
                                               font=('Helvetica', 10, 'italic'), fg=Style.COLOR_ACCENT_BLUE,
                                               bg=Style.BG_PRIMARY, anchor='w')
        self.dynamic_feedback_label.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 10))

        # --- Inputs Card Container ---
        input_card = tk.Frame(main_frame, bg=Style.BG_CARD, padx=20, pady=15, bd=2, relief=tk.GROOVE)
        input_card.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(0, 20))
        input_card.grid_columnconfigure(1, weight=1)

        # Helper function for consistent row styling with Tooltip
        row_idx = 0
        def create_input_row(parent, label_text, widget, tooltip_text=""):
            nonlocal row_idx
            label = tk.Label(parent, text=label_text, font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#555555')
            label.grid(row=row_idx, column=0, sticky='w', pady=(5, 5), padx=(0, 15))
            widget.grid(row=row_idx, column=1, pady=(5, 5), sticky='w')

            if tooltip_text:
                Tooltip(label, tooltip_text)

            row_idx += 1
            return widget

        # 1. Unit Selection
        unit_frame = tk.Frame(input_card, bg=Style.BG_CARD)
        tk.Label(input_card, text="Units:", font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#555555').grid(row=row_idx, column=0, sticky='w', pady=(5, 5), padx=(0, 15))
        unit_frame.grid(row=row_idx, column=1, pady=(5, 5), sticky='w')
        row_idx += 1

        tk.Radiobutton(unit_frame, text="Metric (kg/m)", variable=self.unit_system, value="metric", command=self.update_unit_labels, font=Style.FONT_LABEL, bg=Style.BG_CARD, activebackground=Style.BG_PRIMARY, selectcolor=Style.COLOR_ACCENT_BLUE).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(unit_frame, text="Imperial (lbs/ft/in)", variable=self.unit_system, value="imperial", command=self.update_unit_labels, font=Style.FONT_LABEL, bg=Style.BG_CARD, activebackground=Style.BG_PRIMARY, selectcolor=Style.COLOR_ACCENT_BLUE).pack(side=tk.LEFT, padx=5)

        # 2. Name
        self.name_entry = tk.Entry(input_card, font=Style.FONT_INPUT, relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor=Style.COLOR_ACCENT_BLUE, bg='#F5F5F5')
        create_input_row(input_card, "Your Name:", self.name_entry, "Enter your name for plan personalization.")

        # 3. Gender
        gender_frame = tk.Frame(input_card, bg=Style.BG_CARD)
        tk.Label(input_card, text="Gender:", font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#555555').grid(row=row_idx, column=0, sticky='w', pady=(5, 5), padx=(0, 15))
        gender_frame.grid(row=row_idx, column=1, pady=(5, 5), sticky='w')
        row_idx += 1

        tk.Radiobutton(gender_frame, text="Male", variable=self.gender, value="Male", font=Style.FONT_LABEL, bg=Style.BG_PRIMARY, fg='#333333', indicatoron=0, bd=1, relief=tk.RAISED, selectcolor=Style.COLOR_ACCENT_BLUE, width=7).pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(gender_frame, text="Female", variable=self.gender, value="Female", font=Style.FONT_LABEL, bg=Style.BG_PRIMARY, fg='#333333', indicatoron=0, bd=1, relief=tk.RAISED, selectcolor=Style.COLOR_ACCENT_BLUE, width=7).pack(side=tk.LEFT)

        # 4. Age
        self.age_entry = tk.Entry(input_card, font=Style.FONT_INPUT, relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor=Style.COLOR_ACCENT_BLUE, bg='#F5F5F5')
        create_input_row(input_card, "Age (Years):", self.age_entry, "Your age is used for Basal Metabolic Rate (BMR) calculation.")

        # 5. Activity Level
        self.activity_menu = tk.OptionMenu(input_card, self.activity_level, *self.ACTIVITY_OPTIONS, command=self.update_activity_explanation)
        self.activity_menu.config(width=15, font=Style.FONT_LABEL, bg=Style.BG_PRIMARY, activebackground=Style.COLOR_ACCENT_BLUE, relief=tk.RAISED, bd=1)
        create_input_row(input_card, "Activity Level:", self.activity_menu, "Select the option that best reflects your weekly exercise routine.")

        self.activity_explanation_label = tk.Label(input_card, text=self.ACTIVITY_EXPLANATIONS[self.activity_level.get()],
                                                     font=('Helvetica', 9, 'italic'), fg='#666666', bg=Style.BG_CARD, justify=tk.LEFT, wraplength=400)
        self.activity_explanation_label.grid(row=row_idx, column=0, columnspan=2, sticky='w', padx=5, pady=(0, 10))
        row_idx += 1

        # 6. Health Goal
        self.goal_menu = tk.OptionMenu(input_card, self.health_goal, *self.goal_options)
        self.goal_menu.config(width=15, font=Style.FONT_LABEL, bg=Style.BG_PRIMARY, activebackground=Style.COLOR_ACCENT_BLUE, relief=tk.RAISED, bd=1)
        create_input_row(input_card, "Health Goal:", self.goal_menu, "Your goal determines your calorie surplus or deficit.")

        # 7. Diet Preference
        self.diet_menu = tk.OptionMenu(input_card, self.diet_preference, *self.DIET_OPTIONS)
        self.diet_menu.config(width=15, font=Style.FONT_LABEL, bg=Style.BG_PRIMARY, activebackground=Style.COLOR_ACCENT_BLUE, relief=tk.RAISED, bd=1)
        create_input_row(input_card, "Diet Preference:", self.diet_menu, "This refines protein and meal suggestions in your plan.")

        # 8. Weight Input (Dynamic)
        self.weight_label = tk.Label(input_card, textvariable=self.weight_label_text, font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#555555')
        self.weight_entry = tk.Entry(input_card, font=Style.FONT_INPUT, relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor=Style.COLOR_ACCENT_BLUE, bg='#F5F5F5')
        create_input_row(input_card, "Weight:", self.weight_entry, "Enter your current weight.")

        # 9. Height Input (Dynamic)
        self.height_label = tk.Label(input_card, textvariable=self.height_label_text, font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#555555')
        self.height_label.grid(row=row_idx, column=0, sticky='w', pady=(5, 5), padx=(0, 15))
        self.height_input_frame = tk.Frame(input_card, bg=Style.BG_CARD)
        self.height_input_frame.grid(row=row_idx, column=1, pady=(5, 5), sticky='w')
        row_idx += 1

        Tooltip(self.height_label, "Enter your height. Units depend on the unit system selected.")

        # Metric input (m)
        self.metric_height_entry = tk.Entry(self.height_input_frame, width=15, font=Style.FONT_INPUT, relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor=Style.COLOR_ACCENT_BLUE, bg='#F5F5F5')

        # Imperial inputs (ft and in)
        self.ft_entry = tk.Entry(self.height_input_frame, width=5, font=Style.FONT_INPUT, relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor=Style.COLOR_ACCENT_BLUE, bg='#F5F5F5')
        self.in_entry = tk.Entry(self.height_input_frame, width=5, font=Style.FONT_INPUT, relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor=Style.COLOR_ACCENT_BLUE, bg='#F5F5F5')

        # --- Control Buttons Frame ---
        button_frame = tk.Frame(main_frame, bg=Style.BG_PRIMARY)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)

        self.calculate_button = tk.Button(button_frame, text="Calculate BMI", command=self.calculate_bmi_gui,
                                             bg=Style.COLOR_ACCENT_GREEN, fg='white', font=('Helvetica', 14, 'bold'),
                                             relief=tk.RAISED, padx=30, pady=10, activebackground=Style.COLOR_BUTTON_HOVER, bd=4)
        self.calculate_button.pack(side=tk.LEFT, padx=15)

        self.clear_button = tk.Button(button_frame, text="Clear", command=self.clear_inputs,
                                      bg='#CCCCCC', fg='#555555', font=('Helvetica', 12),
                                      relief=tk.RAISED, padx=20, pady=8, activebackground='#BBBBBB', bd=2)
        self.clear_button.pack(side=tk.LEFT, padx=15)

        # --- Result Card Container ---
        self.result_frame = tk.Frame(main_frame, bg=Style.BG_CARD, padx=20, pady=20, bd=2, relief=tk.GROOVE)
        self.result_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(10, 20))
        self.result_frame.grid_columnconfigure(0, weight=1)
        self.result_frame.grid_columnconfigure(1, weight=1)

        # Result Labels setup
        tk.Label(self.result_frame, text="BMI Value:", font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#333').grid(row=0, column=0, sticky='w', pady=2)
        self.bmi_value_label = tk.Label(self.result_frame, text="---", font=Style.FONT_RESULT_VALUE, bg=Style.BG_CARD, fg='#333333')
        self.bmi_value_label.grid(row=0, column=1, sticky='e', padx=10)

        tk.Label(self.result_frame, text="Category:", font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#333').grid(row=1, column=0, sticky='w', pady=5)
        self.category_label = tk.Label(self.result_frame, text="---", font=Style.FONT_CATEGORY, bg=Style.BG_CARD, fg='#0000FF')
        self.category_label.grid(row=1, column=1, sticky='e', padx=10)

        tk.Label(self.result_frame, text="Ideal Weight Range:", font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#333').grid(row=2, column=0, sticky='w', pady=5)
        self.ideal_weight_label = tk.Label(self.result_frame, text="---", font=Style.FONT_INPUT, bg=Style.BG_CARD, fg=Style.COLOR_ACCENT_GREEN)
        self.ideal_weight_label.grid(row=2, column=1, sticky='e', padx=10)

        # Goal Difference Label (Clear placeholder)
        self.goal_diff_label = tk.Label(self.result_frame, text="", font=Style.FONT_INPUT, bg=Style.BG_CARD, fg=Style.COLOR_ACCENT_BLUE)

        # Warnings/Benefits Labels
        tk.Label(self.result_frame, text="Health Guidance:", font=('Helvetica', 10, 'bold'), bg=Style.BG_CARD, fg='#333', anchor='w').grid(row=4, column=0, sticky='w', pady=(10, 0))

        self.warning_label = tk.Label(self.result_frame, text="---", wraplength=450, justify=tk.LEFT, font=('Helvetica', 9), bg=Style.BG_CARD, fg=Style.COLOR_DANGER)
        self.warning_label.grid(row=5, column=0, columnspan=2, sticky='w', padx=5, pady=(5, 5))

        self.benefit_label = tk.Label(self.result_frame, text="---", wraplength=450, justify=tk.LEFT, font=('Helvetica', 9), bg=Style.BG_CARD, fg=Style.COLOR_ACCENT_GREEN)
        self.benefit_label.grid(row=6, column=0, columnspan=2, sticky='w', padx=5, pady=(0, 5))

        # History Button
        history_button = tk.Button(main_frame, text="View BMI History & Chart", command=self.show_history,
                                             bg=Style.COLOR_ACCENT_BLUE, fg='white', font=('Helvetica', 11, 'bold'), relief=tk.RAISED,
                                             padx=10, pady=6, activebackground='#0056b3', bd=2)
        history_button.grid(row=5, column=0, columnspan=2, pady=(15, 0))

        self.update_unit_labels() # Initial setup call


    # --- PLANNER VIEW SETUP ---
    def setup_planner_frame(self):
        """Builds the Health Planner UI with new tracking features (Goal Tracker removed)."""
        planner_frame = tk.Frame(self.content_container, bg=Style.BG_PRIMARY)
        self.frames['Planner'] = planner_frame
        planner_frame.grid(row=0, column=0, sticky='nsew')

        # --- Scrollable Setup for Planner ---
        scroll_canvas = tk.Canvas(planner_frame, bg=Style.BG_PRIMARY, bd=0, highlightthickness=0)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(planner_frame, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        main_planner_frame = tk.Frame(scroll_canvas, bg=Style.BG_PRIMARY, padx=10, pady=10)
        scroll_canvas.create_window((0, 0), window=main_planner_frame, anchor="nw", width=550)
        main_planner_frame.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))

        main_planner_frame.grid_columnconfigure(0, weight=1)

        tk.Label(main_planner_frame, text="Health Planner & Tracking", font=Style.FONT_HEADING, bg=Style.BG_PRIMARY, fg='#333').grid(row=0, column=0, sticky='w', pady=(0, 10))

        row_idx = 1 # Start row index at 1 (Row 0 is the header)

        # 1. Hydration Tracker Card (This was item 2, now item 1)
        hydration_card = tk.Frame(main_planner_frame, bg=Style.BG_CARD, padx=20, pady=15, bd=2, relief=tk.GROOVE)
        hydration_card.grid(row=row_idx, column=0, sticky='ew', pady=(0, 15))
        hydration_card.grid_columnconfigure(0, weight=1)
        hydration_card.grid_columnconfigure(1, weight=1)
        row_idx += 1

        tk.Label(hydration_card, text="💧 Daily Hydration Tracker", font=Style.FONT_CATEGORY, bg=Style.BG_CARD, fg=Style.COLOR_WATER).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))

        # Hydration Goal Display
        tk.Label(hydration_card, text=f"Goal: {self.WATER_GOAL_ML}ml (approx 8 glasses)", font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#555').grid(row=1, column=0, sticky='w', pady=5)

        # Progress Bar and Label
        self.water_bar = ttk.Progressbar(hydration_card, orient='horizontal', length=150, mode='determinate', style='TProgressbar')
        self.water_bar.grid(row=2, column=0, sticky='ew', columnspan=2, pady=(5, 5))
        self.water_status_label = tk.Label(hydration_card, textvariable=self.water_intake_ml, font=Style.FONT_INPUT, bg=Style.BG_CARD, fg=Style.COLOR_WATER)
        self.water_status_label.grid(row=3, column=0, columnspan=2, sticky='e')

        # Log Water Input
        water_log_frame = tk.Frame(hydration_card, bg=Style.BG_CARD)
        water_log_frame.grid(row=4, column=0, columnspan=2, sticky='w', pady=(10, 5))
        tk.Label(water_log_frame, text="Log intake (ml):", font=Style.FONT_LABEL, bg=Style.BG_CARD).pack(side=tk.LEFT)
        tk.Entry(water_log_frame, textvariable=self.water_add_ml, width=8, font=Style.FONT_INPUT, relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor=Style.COLOR_ACCENT_BLUE).pack(side=tk.LEFT, padx=5)
        tk.Button(water_log_frame, text="Add Water", command=self.log_water_intake, bg=Style.COLOR_ACCENT_BLUE, fg='white', font=('Helvetica', 10, 'bold'), relief=tk.RAISED, bd=2).pack(side=tk.LEFT)

        self.update_hydration_display() # Initial hydration display update is safe now

        # 2. Schedule Chart Area (This was item 3, now item 2)
        tk.Label(main_planner_frame, text="Daily Schedule Timeline (8:00 to 22:00)", font=Style.FONT_CATEGORY, bg=Style.BG_PRIMARY).grid(row=row_idx, column=0, sticky='w', pady=(15, 5))
        row_idx += 1
        self.schedule_canvas = tk.Canvas(main_planner_frame, width=550, height=150, bg=Style.BG_CARD, bd=1, relief=tk.RIDGE)
        self.schedule_canvas.grid(row=row_idx, column=0, sticky='ew', pady=5)
        row_idx += 1

        # 3. Meal Suggestions Card (This was item 4, now item 3)
        tk.Label(main_planner_frame, text="🍽️ Meal Suggestions", font=Style.FONT_CATEGORY, bg=Style.BG_PRIMARY).grid(row=row_idx, column=0, sticky='w', pady=(15, 5))
        row_idx += 1

        meal_card = tk.Frame(main_planner_frame, bg=Style.BG_CARD, padx=15, pady=10, bd=2, relief=tk.GROOVE)
        meal_card.grid(row=row_idx, column=0, sticky='ew', pady=(0, 15))
        row_idx += 1

        self.meal_suggestions_text = tk.Text(meal_card, wrap=tk.WORD, height=8, font=('Helvetica', 10), bg='#F5F5F5', bd=1, padx=10, pady=10, relief=tk.FLAT)
        self.meal_suggestions_text.pack(fill=tk.BOTH, expand=True)

        # 4. Detailed Plan & Guidance (This was item 5, now item 4)
        tk.Label(main_planner_frame, text="Detailed Plan & Guidance", font=Style.FONT_CATEGORY, bg=Style.BG_PRIMARY).grid(row=row_idx, column=0, sticky='w', pady=(15, 5))
        row_idx += 1

        plan_text_frame = tk.Frame(main_planner_frame, bg=Style.BG_CARD, bd=2, relief=tk.GROOVE)
        plan_text_frame.grid(row=row_idx, column=0, sticky='ew', pady=(0, 10), ipady=5)
        row_idx += 1

        self.plan_text_widget = tk.Text(plan_text_frame, wrap=tk.WORD, font=('Helvetica', 10), bg='#F5F5F5', bd=1, padx=10, pady=10, relief=tk.FLAT, height=15)

        scrollbar = tk.Scrollbar(plan_text_frame, command=self.plan_text_widget.yview)
        self.plan_text_widget['yscrollcommand'] = scrollbar.set

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.plan_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 5. Export Button (This was item 6, now item 5)
        self.export_btn = tk.Button(main_planner_frame, text="Export Plan (TXT/PDF)",
                                 command=lambda: self.export_plan(self.plan_text_widget.get("1.0", tk.END)),
                                 bg=Style.COLOR_ACCENT_BLUE, fg='white', font=('Helvetica', 11, 'bold'),
                                 relief=tk.RAISED, padx=15, pady=6, activebackground='#0056b3', bd=3,
                                 state=tk.DISABLED)
        self.export_btn.grid(row=row_idx, column=0, pady=10)

    def view_plan(self):
        """
        Switches to the Planner frame, updates the plan content based on current inputs,
        and enables the export button.
        """
        if not self.current_inputs:
            messagebox.showinfo("Information", "Please calculate your BMI first in the Calculator tab.")
            return

        plan_text = self.generate_diet_plan(self.current_inputs)

        # 1. Update Detailed Plan Text Widget
        self.plan_text_widget.config(state=tk.NORMAL)
        self.plan_text_widget.delete('1.0', tk.END)
        self.plan_text_widget.insert(tk.END, plan_text)
        self.plan_text_widget.config(state=tk.DISABLED)

        # 2. Update Meal Suggestions Widget
        meal_suggestions = self.generate_meal_suggestions(self.current_inputs)
        self.meal_suggestions_text.config(state=tk.NORMAL)
        self.meal_suggestions_text.delete('1.0', tk.END)
        self.meal_suggestions_text.insert(tk.END, meal_suggestions)
        self.meal_suggestions_text.config(state=tk.DISABLED)

        # 3. Draw Schedule Chart
        self.draw_schedule_chart(self.schedule_canvas, self.current_inputs)

        # 4. Enable Export Button
        self.export_btn.config(state=tk.NORMAL)

        # 5. Switch Frame
        self.show_frame('Planner')

    # --- CORE METHODS ---

    def update_activity_explanation(self, *args):
        level = self.activity_level.get()
        self.activity_explanation_label.config(text=self.ACTIVITY_EXPLANATIONS.get(level, ""))

    def log_water_intake(self):
        try:
            amount = int(self.water_add_ml.get())
            if amount <= 0:
                raise ValueError

            current = self.water_intake_ml.get()
            self.water_intake_ml.set(current + amount)
            self.update_hydration_display()
            self.water_add_ml.set("250") # Reset for next log

        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid positive number for water intake (ml).")

    def update_hydration_display(self):
        # Check if hydration widgets have been initialized (AttributeError fix)
        if self.water_bar is None or self.water_status_label is None:
            return

        current = self.water_intake_ml.get()
        progress = min(100, (current / self.WATER_GOAL_ML) * 100)

        self.water_bar['value'] = progress
        self.water_status_label.config(text=f"{current}ml / {self.WATER_GOAL_ML}ml ({progress:.0f}%)")

        if progress >= 100:
            self.water_status_label.config(fg=Style.COLOR_ACCENT_GREEN)
        else:
            self.water_status_label.config(fg=Style.COLOR_WATER)

    def load_history(self):
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r') as f:
                    self.history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.history = []
                messagebox.showwarning("History Load Error", "Could not load or parse BMI history file.")
        else:
            self.history = []

    def save_history(self, inputs, bmi, category):
        unit = inputs['unit']

        if unit == 'metric':
            weight_str = f"{inputs['weight']} kg"
            height_str = f"{inputs['height']:.2f} m"
        else:
            # Imperial height stored as total inches (ft*12 + in)
            height_inches = inputs['height']
            feet = int(height_inches // 12)
            inches = round(height_inches % 12)
            weight_str = f"{inputs['weight']} lbs"
            height_str = f"{feet} ft {inches} in"

        new_record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "bmi": round(bmi, 2), "category": category,
            "weight": weight_str,
            "height": height_str,
        }
        self.history.append(new_record)
        self.history = self.history[-20:]

        try:
            with open(self.HISTORY_FILE, 'w') as f:
                json.dump(self.history, f, indent=4)
        except IOError:
            messagebox.showerror("History Save Error", "Could not save BMI history to file.")

    def clear_inputs(self):
        self.name_entry.delete(0, tk.END)
        self.weight_entry.delete(0, tk.END)
        self.metric_height_entry.delete(0, tk.END)
        self.ft_entry.delete(0, tk.END)
        self.in_entry.delete(0, tk.END)
        self.age_entry.delete(0, tk.END)

        self.current_inputs = {}
        self.water_intake_ml.set(0) # Reset hydration
        self.update_hydration_display()

        # Reset result labels and colors
        self.bmi_value_label.config(text="---", fg='#333333')
        self.category_label.config(text="---", fg='#0000FF')
        self.ideal_weight_label.config(text="---", fg=Style.COLOR_ACCENT_GREEN)
        self.goal_diff_label.config(text="") # Resetting empty text
        self.warning_label.config(text="---", fg=Style.COLOR_DANGER)
        self.benefit_label.config(text="---", fg=Style.COLOR_ACCENT_GREEN)
        self.result_frame.config(bg=Style.BG_CARD)
        self.dynamic_feedback_label.config(text="💡 Enter your details to get started!", fg=Style.COLOR_ACCENT_BLUE)

        self.weight_entry.focus_set()

        for widget in self.result_frame.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(bg=Style.BG_CARD)

    def update_unit_labels(self):
        unit = self.unit_system.get()

        for widget in self.height_input_frame.winfo_children():
            widget.pack_forget()

        if unit == "metric":
            self.weight_label_text.set("Weight (kg):")
            self.height_label_text.set("Height (m):")
            self.metric_height_entry.pack(side=tk.LEFT)
        else: # imperial
            self.weight_label_text.set("Weight (lbs):")
            self.height_label_text.set("Height:")

            self.ft_entry.pack(side=tk.LEFT, ipady=2)
            tk.Label(self.height_input_frame, text=" ft ", font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#555555').pack(side=tk.LEFT)
            self.in_entry.pack(side=tk.LEFT, ipady=2, padx=(5,0))
            tk.Label(self.height_input_frame, text=" in", font=Style.FONT_LABEL, bg=Style.BG_CARD, fg='#555555').pack(side=tk.LEFT)

        self.clear_inputs()

    def validate_and_get_inputs(self):
        name = self.name_entry.get().strip()
        if not name:
            self.dynamic_feedback_label.config(text="⚠️ Please enter your name to personalize the plan.", fg=Style.COLOR_DANGER)
            return None

        unit = self.unit_system.get()

        try:
            weight = float(self.weight_entry.get())
            age = int(self.age_entry.get())

            if unit == 'metric':
                height = float(self.metric_height_entry.get())
            else:
                feet = float(self.ft_entry.get() or 0)
                inches = float(self.in_entry.get() or 0)
                # Height is stored as total inches for imperial to standardize the 'height' key
                height = (feet * 12) + inches

            if weight <= 0 or height <= 0:
                self.dynamic_feedback_label.config(text="⚠️ Weight and Height must be positive numbers.", fg=Style.COLOR_DANGER)
                return None

            if not (16 <= age <= 120): # Adjusted minimum age for adult BMI
                self.dynamic_feedback_label.config(text="⚠️ Age must be between 16 and 120 years.", fg=Style.COLOR_DANGER)
                return None

            self.dynamic_feedback_label.config(text="✅ Inputs validated. Ready to calculate!", fg=Style.COLOR_ACCENT_GREEN)

            return {
                "name": name, "weight": weight, "height": height,
                "age": age, "gender": self.gender.get(),
                "activity": self.activity_level.get(),
                "goal": self.health_goal.get(),
                "diet": self.diet_preference.get(),
                "unit": unit
            }

        except ValueError:
            self.dynamic_feedback_label.config(text="❌ Invalid input: Please ensure all fields contain valid numbers.", fg=Style.COLOR_DANGER)
            return None

    def flash_button(self, original_bg=Style.COLOR_ACCENT_GREEN, flash_bg=Style.COLOR_BUTTON_HOVER):
        self.calculate_button.config(bg=flash_bg)
        self.master.after(100, lambda: self.calculate_button.config(bg=original_bg))

    def calculate_ideal_weight(self, height, unit):
        # Convert height to meters for calculation standardisation
        if unit == 'imperial':
            height_m = height * 0.0254 # height is total inches
        else:
            height_m = height # height is already in meters

        min_weight_kg = self.BMI_MIN_NORMAL * (height_m ** 2)
        max_weight_kg = self.BMI_MAX_NORMAL * (height_m ** 2)

        if unit == 'imperial':
            min_weight = min_weight_kg * 2.20462 # convert kg to lbs
            max_weight = max_weight_kg * 2.20462
            unit_display = "lbs"
        else:
            min_weight = min_weight_kg
            max_weight = max_weight_kg
            unit_display = "kg"

        return f"{min_weight:.1f} - {max_weight:.1f} {unit_display}"

    def calculate_bmi_gui(self):
        self.flash_button(Style.COLOR_ACCENT_GREEN)

        inputs = self.validate_and_get_inputs()

        if inputs is None:
            return

        self.current_inputs = inputs
        bmi = self.perform_calculation(inputs["weight"], inputs["height"], inputs["unit"])

        category, color_code, description, bg_color, warning, benefit = self.categorize_bmi(
            bmi, inputs["gender"], inputs["unit"], inputs["age"]
        )
        ideal_range = self.calculate_ideal_weight(inputs["height"], inputs["unit"])

        self.current_inputs["category"] = category
        self.current_inputs["bmi"] = bmi

        self.save_history(inputs, bmi, category)

        # Update GUI labels with colors
        self.bmi_value_label.config(text=f"{bmi:.2f}", bg=bg_color)
        self.category_label.config(text=category, fg=color_code, bg=bg_color)
        self.ideal_weight_label.config(text=ideal_range, bg=bg_color)
        self.goal_diff_label.config(text="") # Clear placeholder

        self.warning_label.config(text=warning, bg=bg_color)
        self.benefit_label.config(text=benefit, bg=bg_color)

        self.result_frame.config(bg=bg_color)

        for widget in self.result_frame.winfo_children():
            if isinstance(widget, tk.Label):
                 widget.config(bg=bg_color)


    def perform_calculation(self, weight, height, unit):
        if unit == 'metric':
            # weight in kg, height in m
            return weight / (height ** 2)
        else:
            # weight in lbs, height in inches
            return (weight / (height ** 2)) * 703

    def categorize_bmi(self, bmi, gender, unit, age):
        """Classifies the BMI and returns category, colors, detailed description, Warning/Benefit strings."""
        warning_prefix = ""

        if bmi < 18.5:
            category, color, bg_color = "Underweight", Style.COLOR_ACCENT_BLUE, '#E3F2FD'
        elif 18.5 <= bmi < 25.0:
            category, color, bg_color = "Normal Weight", Style.COLOR_ACCENT_GREEN, '#E8F5E9'
        elif 25.0 <= bmi < 30.0:
            category, color, bg_color = "Overweight", Style.COLOR_WARNING, '#FFFDE7'
        else:
            category, color, bg_color = "Obesity", Style.COLOR_DANGER, '#FFEBEE'

        if bmi < self.BMI_EXTREME_LOW or bmi > self.BMI_EXTREME_HIGH:
            # IMPROVEMENT: Updated severe alert tone to be a risk indicator
            alert_msg = f"‼️ **SEVERE HEALTH RISK INDICATOR:** Your BMI is {bmi:.2f}. **This tool suggests your value is critically outside the norm.** Seek immediate medical guidance. "
            warning_prefix = alert_msg
            color = Style.COLOR_DANGER
            bg_color = '#FFCDD2'

        if category == "Underweight":
            warning = warning_prefix + "Possible risks: Weakened immune system, anemia, osteoporosis, and fertility issues. Consult a professional."
            benefit = "Benefits of reaching normal weight: Improved energy, stronger bones, and better immune function. Focus on nutrient-dense calories."
        elif category == "Normal Weight":
            warning = warning_prefix + f"Maintain healthy habits. As a {gender.lower()}, ensure adequate protein intake, especially after age 40 (for {age} year old)."
            benefit = "Benefits: Lowest risk of major chronic diseases, better mobility, and higher life expectancy."
        elif category == "Overweight":
            warning = warning_prefix + "Increased risk of: Type 2 diabetes, high blood pressure, and joint problems. Prioritize consistent calorie deficit and activity."
            benefit = "Benefits of losing weight: Lower blood pressure, better sleep quality, improved energy levels, and reduced joint strain."
        else:
            warning = warning_prefix + "High risk of: Severe cardiovascular disease, stroke, sleep apnea, and reduced mobility. Start with low-impact activity immediately."
            benefit = "Benefits of weight management: Dramatic reduction in disease risk, increased mobility, and improved overall mental health."

        description = "Check warnings for details."

        return category, color, description, bg_color, warning, benefit

    # --- Plan Generation and Export ---

    def generate_meal_suggestions(self, inputs):
        """Generates meal suggestions based on diet and goal."""
        diet = inputs.get("diet", "Omnivore")
        goal = inputs.get("goal", "Maintain Weight")

        base_meals = {
            "Omnivore": {
                "Breakfast": ["Scrambled Eggs with Spinach and Whole-Grain Toast.", "Oatmeal with Berries and Nuts."],
                "Lunch": ["Grilled Chicken Salad with Olive Oil Vinaigrette.", "Tuna sandwich on whole wheat."],
                "Dinner": ["Baked Salmon with Quinoa and Roasted Asparagus.", "Lean Beef Stir-fry with Brown Rice."],
            },
            "Vegetarian": {
                "Breakfast": ["Greek Yogurt with Granola and Honey.", "Tofu Scramble with Bell Peppers."],
                "Lunch": ["Lentil Soup and a Side Salad.", "Cheese and Veggie Wrap."],
                "Dinner": ["Black Bean Burgers on Whole Wheat Buns.", "Chickpea Curry with Brown Rice."],
            },
            "Vegan": {
                "Breakfast": ["Tofu Scramble with Nutritional Yeast and Veggies.", "Chia Seed Pudding with Fruit."],
                "Lunch": ["Large Quinoa Salad with Roasted Vegetables and Hummus.", "Vegetable and Bean Chili."],
                "Dinner": ["Lentil Shepherd's Pie.", "Pad Thai with Peanut Sauce and Tofu."],
            }
        }

        meal_plan = f"Meal Suggestions for: **{diet}** Diet ({goal})\n"

        for meal, suggestions in base_meals.get(diet, base_meals['Omnivore']).items():
            meal_plan += f"\n-- {meal} --\n"
            for suggestion in suggestions:
                if goal == "Lose Weight":
                    suggestion += " (Focus on smaller portion size)"
                elif goal == "Gain Muscle":
                    suggestion += " (Add a source of healthy fats/protein)"

                meal_plan += f"* {suggestion}\n"

        return meal_plan

    def generate_diet_plan(self, inputs):
        """Generates a sample diet and activity plan based on all user inputs."""
        name = inputs.get("name", "User")
        category = inputs.get("category", "N/A")
        age = inputs.get("age", "N/A")
        gender = inputs.get("gender", "N/A")
        activity = inputs.get("activity", "N/A")
        goal = inputs.get("goal", "N/A")
        bmi = inputs.get("bmi", 0)
        diet = inputs.get("diet", "Omnivore")
        unit = inputs.get("unit", "metric")

        # Standardize weight/height for BMR calculation (to kg and cm)
        if unit == 'imperial':
            weight_kg = inputs['weight'] / 2.20462
            height_cm = inputs['height'] * 2.54 # height is total inches
        else:
            weight_kg = inputs['weight']
            height_cm = inputs['height'] * 100

        # Harris-Benedict BMR Calculation
        if gender == 'Male':
            bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
        else:
            bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)

        activity_multiplier = self.ACTIVITY_MULTIPLIERS.get(activity, 1.55)
        tdee = bmr * activity_multiplier

        # Calorie Target based on Goal
        if goal == "Lose Weight":
            cal_target = tdee - 500
            goal_advice = "Targeting a calorie deficit of ~500 kcal/day for safe weight loss."
            macros = {'P': 0.35, 'C': 0.40, 'F': 0.25}
        elif goal == "Gain Muscle":
            cal_target = tdee + 300
            goal_advice = "Targeting a calorie surplus of ~300 kcal/day, focusing heavily on protein."
            macros = {'P': 0.30, 'C': 0.50, 'F': 0.20}
        else: # Maintain
            cal_target = tdee
            goal_advice = "Targeting maintenance calories (TDEE) for a balanced lifestyle."
            macros = {'P': 0.25, 'C': 0.45, 'F': 0.30}

        prot_g = round((cal_target * macros['P']) / 4)
        carb_g = round((cal_target * macros['C']) / 4)
        fat_g = round((cal_target * macros['F']) / 9)

        # Motivational Tip / Reminder
        if age > 50:
            reminder = "👵👴 Health Tip: Prioritize calcium and Vitamin D intake for bone health. Daily low-impact exercise is key!"
        elif category in ["Overweight", "Obesity"]:
            reminder = "💧 Hydration Tip: Drink a large glass of water before every meal to aid digestion and satiety."
        elif activity == "Extra Active":
            reminder = "💤 Recovery Tip: Ensure 7-9 hours of quality sleep nightly to repair muscle tissue."
        else:
            reminder = "🧘 Wellness Tip: Manage stress through mindfulness or short breaks. Focus on whole foods, fiber, and consistency."

        header = f"**{name}'s Personalized Health Plan**\n\n"
        details = (
            f"**Current Status Summary:**\n"
            f"  - BMI: {bmi:.2f} ({category})\n"
            f"  - Age / Gender: {age} / {gender}\n"
            f"  - Activity Level: {activity}\n"
            f"  - Diet Preference: **{diet}**\n"
            f"  - Health Goal: **{goal}**\n\n"
            f"**DAILY NUTRITION TARGETS:**\n"
            f"  - Calorie Intake: **{cal_target:.0f} kcal** (TDEE: {tdee:.0f}) | {goal_advice}\n"
            f"  - Macros Breakdown:\n"
            f"    - Protein: {prot_g}g ({macros['P'] * 100:.0f}%)\n"
            f"    - Carbs: {carb_g}g ({macros['C'] * 100:.0f}%)\n"
            f"    - Fats: {fat_g}g ({macros['F'] * 100:.0f}%)\n\n"
            f"*{reminder}*\n"
            f"----------------------------------------------\n"
        )

        # Personalized Diet/Activity Guidance based on Issue (BMI Category)
        if category == "Underweight":
            issue_header = "Addressing the **Underweight** Issue (Focus: Safe Gain)"
            plan_content = (
                f"**Diet Focus (Caloric Surplus):** Focus on maximizing nutrient density in every meal. Choose whole grains, healthy oils (avocado, coconut), nuts, and seeds. Liquid calories like smoothies with protein powder are excellent.\n"
                f"**Activity Focus:** Prioritize **Resistance Training** (Strength) 4 days/week to build muscle mass (muscle weighs more than fat). Limit excessive steady-state cardio to conserve energy."
            )

        elif category == "Overweight" or category == "Obesity":
            issue_header = f"Addressing the **{category}** Issue (Focus: Sustainable Loss)"
            plan_content = (
                f"**Diet Focus (Caloric Deficit):** Must adhere strictly to the calorie target. Prioritize high-fiber foods (vegetables, legumes) and lean protein sources to maximize satiety. Avoid all high-sugar drinks and refined carbohydrates.\n"
                f"**Activity Focus:** Start with daily **Low-Impact Cardio** (e.g., brisk walking, swimming) for 30-60 mins, 5 days/week. Add **Strength Training** (2 days/week) to boost metabolism and preserve muscle mass. "
            )

        else: # Normal Weight / Maintain
            issue_header = "Addressing **Normal Weight** (Focus: Optimization)"
            plan_content = (
                f"**Diet Focus (Balanced Macros):** Rotate your protein and vegetable sources frequently for diverse micronutrients. Adjust {goal.lower()} calories weekly based on performance and scale trends. Stay consistent with your **{diet}** preference.\n"
                f"**Activity Focus:** Ideal is a mix of **Cardio and Strength Training** (4-6 total sessions/week) to maintain health and {goal.lower()}.\n"
                "Sample Meal Tip: Rotate your protein and vegetable sources to ensure a wide spectrum of essential vitamins and minerals. Plan your meals ahead."
            )

        return header + details + f"**{issue_header}**\n\n" + plan_content

    def export_plan(self, text_content):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Personalized Health Plan"
            )

            if file_path:
                # Remove the unnecessary placeholder text about PDF
                cleaned_text = text_content.strip()
                with open(file_path, 'w') as f:
                    f.write(cleaned_text)
                messagebox.showinfo("Export Successful", f"Your health plan has been saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save file: {e}")

    # --- Charting Methods (Improved Schedule Timeline) ---

    def draw_schedule_chart(self, canvas, inputs):
        """Draws a simplified, attractive daily schedule timeline with health cues."""
        canvas.delete("all")
        width, height, padding = 550, 150, 20
        category, goal = inputs.get("category", "N/A"), inputs.get("goal", "N/A")

        # Define Activity focus based on goal/category
        if category == "Underweight" or goal == "Gain Muscle":
            activity_color, activity_text = Style.COLOR_ACCENT_BLUE, "Strength/Mass Training"
        elif category == "Normal Weight" or goal == "Maintain Weight":
            activity_color, activity_text = Style.COLOR_ACCENT_GREEN, "Mixed Cardio & Strength"
        else:
            activity_color, activity_text = Style.COLOR_DANGER, "Cardio/Walking Focus"

        start_hour, end_hour = 8, 22
        time_range = end_hour - start_hour
        y_axis, line_start, line_end = height / 2, padding, width - padding

        # Main Timeline Line (Thicker and clearer)
        canvas.create_line(line_start, y_axis, line_end, y_axis, fill="#BBBBBB", width=4)

        # Draw Hour Markers and Labels
        for hour in range(start_hour, end_hour + 1, 2):
            x = line_start + (hour - start_hour) * (line_end - line_start) / time_range
            canvas.create_line(x, y_axis - 8, x, y_axis + 8, fill="#999", width=2)
            canvas.create_text(x, y_axis + 25, text=f"{hour}:00", font=('Helvetica', 9), fill="#555")

        def hour_to_x(hour):
            if hour < start_hour: hour = start_hour
            if hour > end_hour: hour = end_hour
            return line_start + (hour - start_hour) * (line_end - line_start) / time_range

        # --- Meals (Top half) ---
        meal_color, meal_outline = '#FFC107', '#FFA000' # Amber for meals

        # Breakfast
        x1, x2 = hour_to_x(8), hour_to_x(9)
        canvas.create_rectangle(x1, y_axis - 40, x2, y_axis - 5, fill=meal_color, outline=meal_outline, width=2)
        canvas.create_text((x1 + x2) / 2, y_axis - 22, text="Breakfast", font=('Helvetica', 8, 'bold'))

        # Lunch
        x1, x2 = hour_to_x(12.5), hour_to_x(13.5)
        canvas.create_rectangle(x1, y_axis - 40, x2, y_axis - 5, fill=meal_color, outline=meal_outline, width=2)
        canvas.create_text((x1 + x2) / 2, y_axis - 22, text="Lunch", font=('Helvetica', 8, 'bold'))

        # Dinner
        x1, x2 = hour_to_x(19), hour_to_x(20)
        canvas.create_rectangle(x1, y_axis - 40, x2, y_axis - 5, fill=meal_color, outline=meal_outline, width=2)
        canvas.create_text((x1 + x2) / 2, y_axis - 22, text="Dinner", font=('Helvetica', 8, 'bold'))

        # --- Activity (Bottom half) ---
        activity_start, activity_end = 17, 18
        x1, x2 = hour_to_x(activity_start), hour_to_x(activity_end)

        # Activity Block
        canvas.create_rectangle(x1, y_axis + 5, x2, y_axis + 40, fill=activity_color, outline=activity_color, width=1)
        canvas.create_text((x1 + x2) / 2, y_axis + 22, text="Activity", font=('Helvetica', 8, 'bold'), fill='white')

        # --- Water Break Cues (Below Activity) ---
        water_times = [9.5, 11, 14.5, 16, 21]
        for time_h in water_times:
            x = hour_to_x(time_h)
            canvas.create_text(x, y_axis + 55, text="💧", font=('Helvetica', 12))

        # Footer text
        canvas.create_text(line_start, height - 5, anchor="w", text=f"Focus: {activity_text} | Water Cues: 5 times daily", font=('Helvetica', 9, 'bold'), fill=activity_color)


    def draw_chart(self, canvas, data):
        """Draws a simple line graph of BMI history on the provided canvas."""
        canvas.delete("all")
        if not data:
            canvas.create_text(250, 100, text="No BMI history yet. Calculate your BMI!", fill="gray", font=Style.FONT_CATEGORY)
            return

        width, height, padding = 480, 250, 30

        bmi_values = [item['bmi'] for item in data]
        dates = [item['date'].split(' ')[0] for item in data]

        min_bmi = math.floor(min(15, min(bmi_values)) / 5) * 5
        max_bmi = math.ceil(max(35, max(bmi_values)) / 5) * 5
        bmi_range = max_bmi - min_bmi

        x_step = (width - 2 * padding) / max(1, len(bmi_values) - 1)

        canvas.create_rectangle(padding, padding, width - padding, height - padding, outline="#AAA", width=1)

        def map_y(bmi):
            if bmi_range == 0: return height / 2
            return height - padding - ((bmi - min_bmi) / bmi_range) * (height - 2 * padding)

        for i in range(5):
            bmi_val = min_bmi + (bmi_range / 4) * i
            y = map_y(bmi_val)
            canvas.create_text(padding - 5, y, anchor="e", text=f"{bmi_val:.0f}", fill="#555", font=('Helvetica', 8))
            canvas.create_line(padding, y, width - padding, y, fill="#EEE", dash=(2, 4))

        y_18_5, y_24_9 = map_y(self.BMI_MIN_NORMAL), map_y(self.BMI_MAX_NORMAL)
        canvas.create_rectangle(padding, y_24_9, width - padding, y_18_5, fill="#E8F5E9", outline="")
        canvas.create_line(padding, y_18_5, width - padding, y_18_5, fill="#888", dash=(4, 2))
        canvas.create_line(padding, y_24_9, width - padding, y_24_9, fill="#888", dash=(4, 2))

        points = []
        for i, bmi in enumerate(bmi_values):
            x, y = padding + i * x_step, map_y(bmi)
            points.append((x, y))

            if bmi < 18.5: point_color = Style.COLOR_ACCENT_BLUE
            elif bmi < 25.0: point_color = Style.COLOR_ACCENT_GREEN
            elif bmi < 30.0: point_color = Style.COLOR_WARNING
            else: point_color = Style.COLOR_DANGER

            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=point_color, outline="white", width=1)

            if i % 2 == 0 or len(bmi_values) <= 5:
                canvas.create_text(x, height - padding + 10, anchor="n", text=dates[i], fill="#555", angle=45, font=('Helvetica', 8))

        if len(points) > 1:
            canvas.create_line(points, fill=Style.COLOR_ACCENT_BLUE, width=3, smooth=True)


    def show_history(self):
        """Opens a new window to display BMI history and chart."""
        history_window = tk.Toplevel(self.master)
        history_window.title(f"{self.name_entry.get() or 'User'}'s BMI History & Trend")
        history_window.config(padx=15, pady=15, bg=Style.BG_PRIMARY)
        history_window.geometry("520x650")
        history_window.resizable(False, False)

        tk.Label(history_window, text="BMI Trend Over Time", font=Style.FONT_CATEGORY, bg=Style.BG_PRIMARY).pack(pady=5)

        chart_canvas = tk.Canvas(history_window, width=480, height=250, bg=Style.BG_CARD, bd=1, relief=tk.RIDGE)
        chart_canvas.pack(pady=10, padx=10)
        self.draw_chart(chart_canvas, self.history)

        tk.Label(history_window, text="Recent Records (Max 20)", font=Style.FONT_CATEGORY, bg=Style.BG_PRIMARY).pack(pady=10)

        list_frame = tk.Frame(history_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        history_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Helvetica', 10), height=10, relief=tk.FLAT, bd=0)
        scrollbar.config(command=history_listbox.yview)

        if self.history:
            history_listbox.insert(tk.END, "Date      | BMI  | Category      | Weight")
            history_listbox.insert(tk.END, "----------|------|---------------|--------")
            for record in reversed(self.history):
                weight_str = record.get('weight', 'N/A')
                line = (
                    f"{record['date'].split(' ')[0]} | {record['bmi']:.2f} | "
                    f"{record['category']:<14} | {weight_str.split(' ')[0]:<6}"
                )
                history_listbox.insert(tk.END, line)
        else:
            history_listbox.insert(tk.END, "No history recorded yet. Calculate your BMI to start tracking.")

        history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = BMICalculatorApp(root)
    root.mainloop()
