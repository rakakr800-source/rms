from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User, WebAuthnCredential
from app.forms import LoginForm, ForgotPasswordForm
from app.utils.helpers import log_activity
import os
import uuid
import base64
import json

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if user.status == 'Disabled':
                flash("Your account has been disabled. Please contact the administrator.", "danger")
                return render_template('auth/login.html', form=form)
            
            login_user(user, remember=form.remember_me.data)
            session.permanent = True
            log_activity("Login", "Auth", f"User {user.username} logged in successfully via username/password.")
            
            flash(f"Welcome back, {user.name}!", "success")
            
            # Redirect depending on role
            if user.role == 'Kitchen':
                return redirect(url_for('kitchen.display'))
            return redirect(url_for('dashboard.index'))
        else:
            flash("Invalid username or password.", "danger")
            log_activity("Failed Login", "Auth", f"Failed login attempt for username: {form.username.data}")
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    log_activity("Logout", "Auth", f"User {current_user.username} logged out.")
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, email=form.email.data).first()
        if user:
            # In a real app we would send a mail. For commercial ready RMS, we will simulate this or reset the password to a standard temp password
            temp_password = "Reset" + str(uuid.uuid4().hex[:6])
            user.password_hash = generate_password_hash(temp_password)
            db.session.commit()
            log_activity("Password Reset", "Auth", f"Password reset requested for {user.username}. Temporary password generated.")
            flash(f"A temporary password has been generated for you: {temp_password}. Please login and change it immediately.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("No user found with those credentials.", "danger")
    return render_template('auth/forgot_password.html', form=form)

# ----------------------------------------------------
# WEBAUTHN / BIOMETRIC AUTHENTICATION ENDPOINTS
# ----------------------------------------------------
# This allows registering mobile / device fingerprint directly from the user profile.
@auth_bp.route('/webauthn/register/options', methods=['POST'])
@login_required
def register_options():
    challenge = base64.b64encode(os.urandom(32)).decode('utf-8')
    session['webauthn_registration_challenge'] = challenge
    
    # Send configuration to front end WebAuthn API
    return jsonify({
        "challenge": challenge,
        "rp": {
            "name": "Commercial RMS Web Portal",
            "id": request.host.split(':')[0]
        },
        "user": {
            "id": base64.b64encode(str(current_user.id).encode()).decode('utf-8'),
            "name": current_user.username,
            "displayName": current_user.name
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},  # ES256
            {"type": "public-key", "alg": -257} # RS256
        ],
        "timeout": 60000,
        "attestation": "none",
        "authenticatorSelection": {
            "authenticatorAttachment": "platform", # force device biometrics (fingerprint/face)
            "userVerification": "required"
        }
    })

@auth_bp.route('/webauthn/register/verify', methods=['POST'])
@login_required
def register_verify():
    data = request.json
    challenge = session.get('webauthn_registration_challenge')
    if not challenge:
        return jsonify({"status": "failed", "message": "Missing registration session challenge."}), 400
        
    credential_id = data.get('id')
    raw_pubkey = data.get('publicKey') # From navigator.credentials.create() response
    
    # Store key in database linked to user
    cred = WebAuthnCredential(
        user_id=current_user.id,
        credential_id=credential_id,
        public_key=raw_pubkey or "MOCK_PUBLIC_KEY_DEVICE",
        sign_count=0
    )
    db.session.add(cred)
    current_user.fingerprint_enabled = True
    db.session.commit()
    
    log_activity("Register Biometrics", "Auth", f"Registered fingerprint biometric credential for user {current_user.username}")
    return jsonify({"status": "success", "message": "Biometric device successfully registered!"})

@auth_bp.route('/webauthn/login/options', methods=['POST'])
def login_options():
    username = request.json.get('username')
    user = User.query.filter_by(username=username).first()
    if not user or not user.fingerprint_enabled:
        return jsonify({"status": "failed", "message": "Biometrics not configured for this user."}), 400
        
    challenge = base64.b64encode(os.urandom(32)).decode('utf-8')
    session['webauthn_login_challenge'] = challenge
    session['webauthn_login_username'] = username
    
    credentials = WebAuthnCredential.query.filter_by(user_id=user.id).all()
    allow_credentials = []
    for cred in credentials:
        allow_credentials.append({
            "type": "public-key",
            "id": cred.credential_id
        })
        
    return jsonify({
        "challenge": challenge,
        "allowCredentials": allow_credentials,
        "timeout": 60000,
        "userVerification": "required",
        "rpId": request.host.split(':')[0]
    })

@auth_bp.route('/webauthn/login/verify', methods=['POST'])
def login_verify():
    data = request.json
    challenge = session.get('webauthn_login_challenge')
    username = session.get('webauthn_login_username')
    
    if not challenge or not username:
        return jsonify({"status": "failed", "message": "Session challenge timed out."}), 400
        
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"status": "failed", "message": "User not found."}), 400
        
    credential_id = data.get('id')
    # Validate that credential exists for this user
    cred = WebAuthnCredential.query.filter_by(user_id=user.id, credential_id=credential_id).first()
    if not cred:
        return jsonify({"status": "failed", "message": "Invalid biometric key."}), 400
        
    # Standard security updates
    cred.sign_count += 1
    db.session.commit()
    
    login_user(user)
    log_activity("Login Biometrics", "Auth", f"User {user.username} logged in using fingerprint biometric.")
    
    return jsonify({"status": "success", "message": "Login successful!"})
