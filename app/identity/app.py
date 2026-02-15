from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import random
import logging
from datetime import datetime

from config import Config
from constants import (
    NATIONALITIES_BY_REGION, ORIENTATIONS, BIO_LENGTHS, IMAGE_TYPES,
    HEADER_IMAGE_TYPES, GENDERS, SKIN_TONES, BIO_STYLES, TUTORIAL_STEPS
)
from services.gemini_service import (
    generate_profile_text, regenerate_bio, construct_image_prompts,
    generate_profile_image, generate_header_image, edit_image
)

app = Flask(__name__)
app.config.from_object(Config)

# Security: Restrict CORS to same origin only (or specific domains)
CORS(app, origins=["http://127.0.0.1:5990", "http://localhost:5990"])

# Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://"
)

# Logging
logger = logging.getLogger(__name__)


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
    )
    return response


def safe_error(e):
    """Return a safe error message without leaking internal details"""
    error_msg = str(e)
    if any(keyword in error_msg.lower() for keyword in ['api_key', 'api key', 'traceback', 'file', 'path']):
        logger.error(f"Internal error: {error_msg}")
        return 'An internal error occurred. Please try again.'
    return error_msg


# ==================== Web Routes ====================

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html',
        regions=list(NATIONALITIES_BY_REGION.keys()),
        nationalities_by_region=NATIONALITIES_BY_REGION,
        orientations=ORIENTATIONS,
        bio_lengths=BIO_LENGTHS,
        image_types=IMAGE_TYPES,
        header_image_types=HEADER_IMAGE_TYPES,
        genders=GENDERS,
        skin_tones=SKIN_TONES,
        bio_styles=BIO_STYLES,
        tutorial_steps=TUTORIAL_STEPS
    )


# ==================== API Routes ====================

@app.route('/api/constants', methods=['GET'])
def get_constants():
    """Get all constants for the frontend"""
    return jsonify({
        'success': True,
        'data': {
            'nationalitiesByRegion': NATIONALITIES_BY_REGION,
            'orientations': ORIENTATIONS,
            'bioLengths': BIO_LENGTHS,
            'imageTypes': IMAGE_TYPES,
            'headerImageTypes': HEADER_IMAGE_TYPES,
            'genders': GENDERS,
            'skinTones': SKIN_TONES,
            'bioStyles': BIO_STYLES,
            'tutorialSteps': TUTORIAL_STEPS
        }
    })


@app.route('/api/profile/generate', methods=['POST'])
@limiter.limit("10 per minute")
def api_generate_profile():
    """Generate a complete profile (text only)"""
    try:
        params = request.get_json()
        if not params:
            return jsonify({'success': False, 'error': 'No parameters provided'}), 400
        
        # Generate text data
        text_data = generate_profile_text(params)
        
        # Construct image prompts
        prompts = construct_image_prompts(params)
        
        # Build profile response
        profile = {
            'name': text_data.get('name', ''),
            'username': text_data.get('username', ''),
            'bio': text_data.get('bio', ''),
            'location': text_data.get('location', ''),
            'website': text_data.get('website', ''),
            'bornDate': text_data.get('bornDate', ''),
            'joinDate': f"يونيو {datetime.now().year - 2}",
            'following': random.randint(50, 500),
            'followers': random.randint(1000, 120000),
            'profilePicPrompt': prompts['profilePicPrompt'],
            'headerImagePrompt': prompts['headerImagePrompt'],
            'profilePictureUrl': '',
            'headerImageUrl': ''
        }
        
        return jsonify({'success': True, 'data': profile})
    
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e)}), 500


@app.route('/api/profile/generate-full', methods=['POST'])
@limiter.limit("10 per minute")
def api_generate_full_profile():
    """Generate a complete profile with images"""
    try:
        params = request.get_json()
        if not params:
            return jsonify({'success': False, 'error': 'No parameters provided'}), 400
        
        # Generate text data
        text_data = generate_profile_text(params)
        
        # Construct image prompts
        prompts = construct_image_prompts(params)
        
        # Generate images
        profile_pic_url = generate_profile_image(prompts['profilePicPrompt'])
        header_image_url = generate_header_image(prompts['headerImagePrompt'])
        
        # Build profile response
        profile = {
            'name': text_data.get('name', ''),
            'username': text_data.get('username', ''),
            'bio': text_data.get('bio', ''),
            'location': text_data.get('location', ''),
            'website': text_data.get('website', ''),
            'bornDate': text_data.get('bornDate', ''),
            'joinDate': f"يونيو {datetime.now().year - 2}",
            'following': random.randint(50, 500),
            'followers': random.randint(1000, 120000),
            'profilePicPrompt': prompts['profilePicPrompt'],
            'headerImagePrompt': prompts['headerImagePrompt'],
            'profilePictureUrl': profile_pic_url,
            'headerImageUrl': header_image_url
        }
        
        return jsonify({'success': True, 'data': profile})
    
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e)}), 500


@app.route('/api/profile/random', methods=['POST'])
@limiter.limit("10 per minute")
def api_generate_random_profile():
    """Generate a random profile"""
    try:
        # Generate random parameters
        random_region = random.choice(list(NATIONALITIES_BY_REGION.keys()))
        random_nationality = random.choice(NATIONALITIES_BY_REGION[random_region])
        random_orientation = random.choice(ORIENTATIONS)
        random_image_type = random.choice(IMAGE_TYPES)
        random_header_type = random.choice(HEADER_IMAGE_TYPES)
        random_bio_style = random.choice(BIO_STYLES)
        random_gender = random.choice(GENDERS)
        random_skin_tone = random.choice(SKIN_TONES)
        
        params = {
            'description': f"شخصية {random_orientation.lower()} من {random_nationality}.",
            'nationality': random_nationality,
            'orientation': random_orientation,
            'bioLength': random.choice(BIO_LENGTHS),
            'imageType': random_image_type,
            'headerImageType': random_header_type,
            'gender': random_gender,
            'skinTone': random_skin_tone,
            'headerText': '',
            'bioStyle': random_bio_style,
            'useCustomPrompts': False,
            'customProfilePicPrompt': '',
            'customHeaderImagePrompt': ''
        }
        
        # Generate text data
        text_data = generate_profile_text(params)
        
        # Construct image prompts
        prompts = construct_image_prompts(params)
        
        # Build profile response
        profile = {
            'name': text_data.get('name', ''),
            'username': text_data.get('username', ''),
            'bio': text_data.get('bio', ''),
            'location': text_data.get('location', ''),
            'website': text_data.get('website', ''),
            'bornDate': text_data.get('bornDate', ''),
            'joinDate': f"يونيو {datetime.now().year - 2}",
            'following': random.randint(50, 500),
            'followers': random.randint(1000, 120000),
            'profilePicPrompt': prompts['profilePicPrompt'],
            'headerImagePrompt': prompts['headerImagePrompt'],
            'profilePictureUrl': '',
            'headerImageUrl': '',
            'params': params
        }
        
        return jsonify({'success': True, 'data': profile})
    
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e)}), 500


@app.route('/api/bio/regenerate', methods=['POST'])
@limiter.limit("15 per minute")
def api_regenerate_bio():
    """Regenerate only the bio"""
    try:
        params = request.get_json()
        if not params:
            return jsonify({'success': False, 'error': 'No parameters provided'}), 400
        
        new_bio = regenerate_bio(params)
        return jsonify({'success': True, 'data': {'bio': new_bio}})
    
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e)}), 500


@app.route('/api/text/regenerate', methods=['POST'])
@limiter.limit("10 per minute")
def api_regenerate_text():
    """Regenerate all text content"""
    try:
        params = request.get_json()
        if not params:
            return jsonify({'success': False, 'error': 'No parameters provided'}), 400
        
        text_data = generate_profile_text(params)
        prompts = construct_image_prompts(params)
        
        return jsonify({
            'success': True,
            'data': {
                **text_data,
                'profilePicPrompt': prompts['profilePicPrompt'],
                'headerImagePrompt': prompts['headerImagePrompt']
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e)}), 500


@app.route('/api/image/generate', methods=['POST'])
@limiter.limit("10 per minute")
def api_generate_image():
    """Generate a single image"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        prompt = data.get('prompt', '')
        image_type = data.get('type', 'profile')  # 'profile' or 'header'
        
        if not prompt:
            return jsonify({'success': False, 'error': 'No prompt provided'}), 400
        
        if image_type == 'header':
            image_url = generate_header_image(prompt)
        else:
            image_url = generate_profile_image(prompt)
        
        return jsonify({'success': True, 'data': {'imageUrl': image_url}})
    
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e)}), 500


@app.route('/api/image/edit', methods=['POST'])
@limiter.limit("10 per minute")
def api_edit_image():
    """Edit an existing image"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        image_data = data.get('imageData', '')
        edit_prompt = data.get('prompt', '')
        
        if not image_data or not edit_prompt:
            return jsonify({'success': False, 'error': 'Missing image data or prompt'}), 400
        
        new_image_url = edit_image(image_data, edit_prompt)
        return jsonify({'success': True, 'data': {'imageUrl': new_image_url}})
    
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e)}), 500


@app.route('/api/image/generate-both', methods=['POST'])
@limiter.limit("10 per minute")
def api_generate_both_images():
    """Generate both profile and header images"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        profile_prompt = data.get('profilePicPrompt', '')
        header_prompt = data.get('headerImagePrompt', '')
        
        if not profile_prompt or not header_prompt:
            return jsonify({'success': False, 'error': 'Missing prompts'}), 400
        
        profile_pic_url = generate_profile_image(profile_prompt)
        header_image_url = generate_header_image(header_prompt)
        
        return jsonify({
            'success': True,
            'data': {
                'profilePictureUrl': profile_pic_url,
                'headerImageUrl': header_image_url
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e)}), 500


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5990)
