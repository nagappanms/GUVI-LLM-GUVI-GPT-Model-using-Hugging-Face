### GUVI_GPT_FINAL_Project

import streamlit as st
import mysql.connector
import bcrypt
import datetime
import re
import json
import torch
import pytz
from transformers import GPT2LMHeadModel, GPT2Tokenizer

# Streamlit:

col1, col2 = st.columns([1, 2])

with col1:
    st.image("guvi_chatGPT_Logo.png" , width=150)

with col2:
    st.markdown('''<h1 style="color:#B22222;">Guvi-GPT Text Generator!</h1>''', unsafe_allow_html=True)


#MYSQL_Localhost_Connection:

connection = mysql.connector.connect(
  host = "gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
  port = 4000,
  user = "4GAELt1HafWncbw.root",
  password = "Z18jDVbfGtSywxyt",
)
mycursor = connection.cursor(buffered=True)

mycursor.execute("CREATE DATABASE IF NOT EXISTS Guvi_GPT")
mycursor.execute('USE Guvi_GPT')

mycursor.execute('''CREATE TABLE IF NOT EXISTS User_data
                    (id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        registered_date TIMESTAMP,
                        last_login TIMESTAMP)''')

def username_exists(username):
    mycursor.execute("SELECT * FROM User_data WHERE username = %s", (username,))
    return mycursor.fetchone() is not None

def email_exists(email):
    mycursor.execute("SELECT * FROM User_data WHERE email = %s", (email,))
    return mycursor.fetchone() is not None

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def create_user(username, password, email, registered_date):
    if username_exists(username):
        return 'username_exists'
    
    if email_exists(email):
        return 'email_exists'
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    mycursor.execute(
        "INSERT INTO User_data (username, password, email, registered_date) VALUES (%s, %s, %s, %s)",
        (username, hashed_password, email, registered_date)
    )
    connection.commit()
    return 'success'

def verify_user(username, password):
    mycursor.execute("SELECT password FROM User_data WHERE username = %s", (username,))
    record = mycursor.fetchone()
    if record and bcrypt.checkpw(password.encode('utf-8'), record[0].encode('utf-8')):
        mycursor.execute("UPDATE User_data SET last_login = %s WHERE username = %s", (datetime.datetime.now(pytz.timezone('Asia/Kolkata')), username))
        connection.commit()
        return True
    return False

def reset_password(username, new_password):
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    mycursor.execute(
        "UPDATE User_data SET password = %s WHERE username = %s",
        (hashed_password, username)
    )
    connection.commit()

# Load the fine-tuned model and tokenizer
model_name_or_path = "fine_tuned_model"
model = GPT2LMHeadModel.from_pretrained(model_name_or_path)

token_name_or_path = "fine_tuned_model" 
tokenizer = GPT2Tokenizer.from_pretrained(token_name_or_path)

# Set the pad_token to eos_token if it's not already set
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Move the model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Define the text generation function
def generate_text(model, tokenizer, seed_text, max_length=100, temperature=1.0, num_return_sequences=1):
    # Tokenize the input text with padding
    inputs = tokenizer(seed_text, return_tensors='pt', padding=True, truncation=True)

    input_ids = inputs['input_ids'].to(device)
    attention_mask = inputs['attention_mask'].to(device)

    # Generate text
    with torch.no_grad():
        output = model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_length=max_length,
            temperature=temperature,
            num_return_sequences=num_return_sequences,
            do_sample=True,
            top_k=50,
            top_p=0.01,
            pad_token_id=tokenizer.eos_token_id  # Ensure padding token is set to eos_token_id
        )

    # Decode the generated text
    generated_texts = []
    for i in range(num_return_sequences):
        generated_text = tokenizer.decode(output[i], skip_special_tokens=True)
        generated_texts.append(generated_text)

    return generated_texts

# Session state management
if 'sign_up_successful' not in st.session_state:
    st.session_state.sign_up_successful = False
if 'login_successful' not in st.session_state:
    st.session_state.login_successful = False
if 'reset_password' not in st.session_state:
    st.session_state.reset_password = False
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'

def home_page():
    st.markdown(f"""# <span style="color:#006400">Welcome, {st.session_state.username}!</span>""", unsafe_allow_html=True)
    st.info('''**Disclaimer:** This application utilizes a GPT-based model for generating responses. While generating responses, it may produce errors or inaccuracies. So, Users are encouraged to verify any critical information independently.
            **Most importantly, please be aware that, This model is not affiliated with or endorsed by Official GUVI EdTech Company.**''')
    
    # Text generation section
    seed_text = st.text_input("**Enter text:**")
    max_length = st.number_input("**Length of Words**", min_value=10, max_value=500, value=100)

    if st.button("Generate"):
        with st.spinner("Generating..."):
            generated_texts = generate_text(model, tokenizer, seed_text, max_length, temperature=0.000001, num_return_sequences=1)
            for i, text in enumerate(generated_texts):
                st.write(f"**Text Generated :**\n{text :}\n")


def login():
    st.subheader(':green[**Login**]')
    with st.form(key='login', clear_on_submit=True):
        username = st.text_input(label='Username', placeholder='Enter Username')
        password = st.text_input(label='Password', placeholder='Enter Password', type='password')
        if st.form_submit_button('**Login**'):
            if not username or not password:
                st.error("Enter all the Credentials")
            elif verify_user(username, password):
                st.session_state.login_successful = True
                st.session_state.username = username
                st.session_state.current_page = 'home'
                st.rerun()
            else:
                st.error("Incorrect Username or Password. Sign Up!, if you don't have an account")
    if not st.session_state.login_successful:
        c1, c2 = st.columns(2)
        with c1:
            st.write(":red[New user?]")
            if st.button('**Sign Up**'):
                st.session_state.current_page = 'sign_up'
                st.rerun()
        with c2:
            st.write(":red[Forgot Password?]")
            if st.button('**Reset Password**'):
                st.session_state.current_page = 'reset_password'
                st.rerun()

def signup():
    st.subheader(':red[**Sign Up**]')
    with st.form(key='signup', clear_on_submit=True):
        email = st.text_input(label='Email', placeholder='Enter Your Email')
        username = st.text_input(label='Username', placeholder='Enter Your Username')
        password = st.text_input(label='Password', placeholder='Enter Your Password', type='password')
        re_password = st.text_input(label='Confirm Password', placeholder='Confirm Your Password', type='password')
        registered_date = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))

        if st.form_submit_button('**Sign Up**'):
            if not email or not username or not password or not re_password:
                st.error("Enter all the Credentials")
            elif not is_valid_email(email):
                st.error("Enter a valid email address")
            elif len(password) <= 3:
                st.error("Password too short")
            elif password != re_password:
                st.error("Passwords do not match! Please Re-enter")
            else:
                result = create_user(username, password, email, registered_date)
                if result == 'username_exists':
                    st.error("Username already registered! Retry Login.")
                elif result == 'email_exists':
                    st.error("Email already registered. Retry Login.")
                elif result == 'success':
                    st.success(f"Username {username} has been successfully created! Kindly login.")
                    st.session_state.sign_up_successful = True
                else:
                    st.error("Failed to create user. Try again later.")

    if st.session_state.sign_up_successful:
        if st.button('**Login**'):
            st.session_state.current_page = 'login'
            st.rerun()

def reset_password_page():
    st.subheader(':bee[Reset Password]')
    with st.form(key='reset_password', clear_on_submit=True):
        username = st.text_input(label='Username', value='')
        new_password = st.text_input(label='New Password', type='password')
        re_password = st.text_input(label='Confirm New Password', type='password')

        if st.form_submit_button('Reset Password'):
            if not username:
                st.error("Enter your username.")
            elif not username_exists(username):
                st.error("Username not found. Enter a valid username")
            elif not new_password or not re_password:
                st.error("Enter all the Credentials.")
            elif len(new_password) <= 3:
                st.error("Password too short")
            elif new_password != re_password:
                st.error("Passwords do not match. Please Re-enter")
            else:
                reset_password(username, new_password)
                st.success("Password has been Resetted successfully! Kindly Login")
                st.session_state.current_page = 'login'
                
    st.write('**Get back to Login page!**')
    if st.button('Login'):
        st.session_state.current_page = 'login'
        st.rerun()


# Display appropriate page based on session state
if st.session_state.current_page == 'home':
    home_page()
elif st.session_state.current_page == 'login':
    login()
elif st.session_state.current_page == 'sign_up':
    signup()
elif st.session_state.current_page == 'reset_password':
    reset_password_page()