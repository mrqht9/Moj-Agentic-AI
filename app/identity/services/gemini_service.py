import google.generativeai as genai
from google import genai as genai_new
from google.genai import types as genai_types
import json
import base64
import re
import os
import uuid
import time
from config import Config

GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'generated')
os.makedirs(GENERATED_DIR, exist_ok=True)

genai.configure(api_key=Config.API_KEY)
genai_client = genai_new.Client(api_key=Config.API_KEY)

MAX_INPUT_LENGTH = 500
PROMPT_INJECTION_PATTERNS = [
    'ignore all', 'ignore previous', 'disregard', 'forget your instructions',
    'system prompt', 'reveal your', 'show me your prompt', 'api key',
    'api_key', 'secret', 'password', 'override', 'jailbreak',
    'DAN', 'developer mode', 'ignore the above',
]

def sanitize_input(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Sanitize user input to prevent prompt injection and limit length"""
    if not isinstance(text, str):
        return ''
    text = text.strip()[:max_length]
    text_lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern in text_lower:
            return ''
    return text


def get_bio_instruction(bio_style: str, nationality: str) -> str:
    """Get bio instruction based on style"""
    instructions = {
        'فصحى': 'The bio must be in formal Modern Standard Arabic (Fusha).',
        'عامية': f"The bio MUST be written in the colloquial dialect of '{nationality}'.",
        'عامي وإنجليزي': f"The bio must be a mix of colloquial Arabic (based on '{nationality}') and English, reflecting a modern teenager's style. It can include slang and code-switching.",
        'إنجليزي': 'The bio must be written entirely in English.',
        'إيموجي فقط': 'The bio must consist ONLY of a creative and relevant sequence of emojis, with no words.'
    }
    return instructions.get(bio_style, instructions['فصحى'])


def generate_profile_text(params: dict) -> dict:
    """Generate profile text using Gemini"""
    description = sanitize_input(params.get('description', ''))
    nationality = sanitize_input(params.get('nationality', ''), 100)
    orientation = sanitize_input(params.get('orientation', ''), 100)
    bio_length = sanitize_input(params.get('bioLength', ''), 50)
    bio_style = sanitize_input(params.get('bioStyle', ''), 50)
    
    if not description:
        raise ValueError('Description is required.')
    
    bio_instruction = get_bio_instruction(bio_style, nationality)
    
    prompt = f"""
    Generate a social media profile primarily in Arabic based on the following properties.
    The response must be a valid JSON object.

    MOST IMPORTANT - The person's description (this MUST be the primary focus of the entire profile):
    "{description}"
    
    Secondary properties:
    - Nationality/Origin: "{nationality}"
    - General Tone: "{orientation}" (this is secondary to the description above)
    - Bio Length: "{bio_length}"
    - Bio Style: "{bio_style}". Specific instruction: {bio_instruction}

    CRITICAL RULES:
    1. The description above is the MOST important input. The name, username, bio, and all content MUST directly reflect this description. For example, if the description says "ممرضة في مستشفى", the profile MUST be about a nurse, NOT about technology or any other topic.
    2. The "General Tone" is only a secondary modifier for style, NOT the topic. The topic comes from the description.

    Based on the above, generate the following JSON fields:
    - name: A creative and credible name that fits the person described. It can be a full name, a nickname (kunya), a pseudonym, or an English name with relevant emojis, mimicking popular social media styles. The name must be attractive and perfectly match the description. The name should be in Arabic unless the style is clearly English-focused.
    - username: An engaging and relevant username. It MUST start with '@' and can only contain English letters, numbers, and underscores. It should be creative and reflect the person described.
    - bio: A bio that strongly reflects the description and nationality. It must strictly adhere to the Bio Style instruction. For colloquial style ('عامية'), it must perfectly match the dialect of the specified nationality.
    - location: A credible location (city, country). Must be in Arabic.
    - website: A personal website link (can be a dummy link like example.com).
    - bornDate: A plausible birth date. Must be in Arabic.
    Except for the username (which must be in English characters) and the bio (which must follow the Bio Style instruction), all other text content should be in Arabic.
    
    Return ONLY the JSON object, no additional text.
    """
    
    model = genai.GenerativeModel(Config.TEXT_MODEL)
    response = model.generate_content(prompt)
    
    text = response.text.strip()
    # Clean up potential markdown code blocks
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {text}")
        raise ValueError("AI response was not valid JSON.")


def regenerate_bio(params: dict) -> str:
    """Regenerate only the bio"""
    description = sanitize_input(params.get('description', ''))
    nationality = sanitize_input(params.get('nationality', ''), 100)
    orientation = sanitize_input(params.get('orientation', ''), 100)
    bio_length = sanitize_input(params.get('bioLength', ''), 50)
    bio_style = sanitize_input(params.get('bioStyle', ''), 50)
    
    bio_instruction = get_bio_instruction(bio_style, nationality)
    
    prompt = f"""
    Regenerate only a bio for a social media profile.
    - Topic: "{description}"
    - Nationality: "{nationality}"
    - Desired Tone/Orientation: "{orientation}". This is a critical instruction. The bio's tone must be very clear.
    - Desired Length: "{bio_length}"
    - Bio Style: "{bio_style}". This is the most important instruction. Strictly follow this: {bio_instruction}
    
    The response should be only the new bio text, without any introductions or titles.
    CRITICAL: If the Bio Style is 'عامية' (colloquial), the generated bio MUST be in the authentic, natural-sounding colloquial dialect of the specified '{nationality}'.
    """
    
    model = genai.GenerativeModel(Config.TEXT_MODEL)
    response = model.generate_content(prompt)
    
    return response.text.strip()


def construct_image_prompts(params: dict) -> dict:
    """Construct prompts for profile and header images"""
    use_custom = bool(params.get('useCustomPrompts', False))
    custom_profile = sanitize_input(params.get('customProfilePicPrompt', ''))
    custom_header = sanitize_input(params.get('customHeaderImagePrompt', ''))
    description = sanitize_input(params.get('description', ''))
    nationality = sanitize_input(params.get('nationality', ''), 100)
    orientation = sanitize_input(params.get('orientation', ''), 100)
    image_type = sanitize_input(params.get('imageType', ''), 100)
    header_image_type = sanitize_input(params.get('headerImageType', ''), 100)
    gender = sanitize_input(params.get('gender', ''), 50)
    skin_tone = sanitize_input(params.get('skinTone', ''), 50)
    header_text = sanitize_input(params.get('headerText', ''), 200)
    
    anti_watermark = "A hyper-realistic, professional photograph. CRITICAL RULE: Absolutely NO text, letters, watermarks, prompts, or any other writing should appear anywhere in the image. The image must be purely visual and completely clean of any text artifacts. This is the most important rule."
    
    if use_custom and custom_profile and custom_header:
        return {
            'profilePicPrompt': f"{custom_profile}. {anti_watermark}",
            'headerImagePrompt': f"{custom_header}. {anti_watermark}"
        }
    
    # Profile picture prompt
    profile_prompt = "A high-quality, professional-looking headshot of a "
    if image_type == 'شخص':
        gender_en = 'man' if gender == 'رجل' else 'woman'
        skin_en = 'light' if skin_tone == 'فاتح' else ('tan' if skin_tone == 'حنطي' else 'dark')
        profile_prompt += f"{gender_en} who is {description}. The person is from {nationality} with authentic cultural features and attire. The person has a {skin_en} skin tone."
    else:
        profile_prompt += f"An image that represents: {description}."
    profile_prompt += f" The style of the image should be: {image_type}. {anti_watermark}"
    
    # Header image prompt
    header_prompt = f"An artistic header image that directly represents: {description}. The style of the image should be: {header_image_type}. The person is from {nationality}. The image should visually reflect the theme of '{description}' with relevant symbols and elements."
    
    if header_text:
        header_prompt += f' The image should artistically incorporate the following English text: "{header_text}". The text should be stylish and well-integrated into the design.'
    else:
        header_prompt += " Avoid any text, letters, or words in the image."
    header_prompt += f" {anti_watermark}"
    
    return {
        'profilePicPrompt': profile_prompt,
        'headerImagePrompt': header_prompt
    }


MAX_GENERATED_FILES = 200
IMAGE_MAX_AGE_SECONDS = 3600  # 1 hour

def _cleanup_old_images():
    """Remove generated images older than IMAGE_MAX_AGE_SECONDS or if count exceeds MAX_GENERATED_FILES"""
    try:
        files = []
        for f in os.listdir(GENERATED_DIR):
            fp = os.path.join(GENERATED_DIR, f)
            if os.path.isfile(fp):
                files.append((fp, os.path.getmtime(fp)))
        
        now = time.time()
        # Delete old files
        for fp, mtime in files:
            if now - mtime > IMAGE_MAX_AGE_SECONDS:
                os.remove(fp)
        
        # If still too many, delete oldest
        files = [(fp, mt) for fp, mt in files if os.path.exists(fp)]
        if len(files) > MAX_GENERATED_FILES:
            files.sort(key=lambda x: x[1])
            for fp, _ in files[:len(files) - MAX_GENERATED_FILES]:
                os.remove(fp)
    except Exception:
        pass


def _save_image_bytes(image_bytes: bytes, ext: str = "png") -> str:
    """Save image bytes to static/generated and return the filename"""
    _cleanup_old_images()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(GENERATED_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(image_bytes)
    return filename


def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
    """Generate an image using Gemini 2.5 Flash Image - Returns URL path on server"""
    
    response = genai_client.models.generate_content(
        model='gemini-2.5-flash-image',
        contents=[prompt],
        config=genai_types.GenerateContentConfig(
            response_modalities=['Image'],
            image_config=genai_types.ImageConfig(
                aspect_ratio=aspect_ratio,
            )
        )
    )
    
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                raw_data = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/png"
                ext = mime_type.split('/')[-1] if '/' in mime_type else 'png'
                if isinstance(raw_data, str):
                    raw_data = base64.b64decode(raw_data)
                filename = _save_image_bytes(raw_data, ext)
                return f"/static/generated/{filename}"
    
    raise ValueError("No image was returned from Gemini.")


def generate_profile_image(prompt: str) -> str:
    """Generate profile picture (1:1 aspect ratio)"""
    return generate_image(prompt, "1:1")


def generate_header_image(prompt: str) -> str:
    """Generate header image (16:9 aspect ratio)"""
    return generate_image(prompt, "16:9")


def edit_image(base64_image_data: str, edit_prompt: str) -> str:
    """Edit an existing image using Gemini - Returns URL path on server"""
    # Extract base64 data
    if ',' in base64_image_data:
        header, data = base64_image_data.split(',', 1)
        mime_type = header.split(':')[1].split(';')[0] if ':' in header else 'image/jpeg'
    else:
        data = base64_image_data
        mime_type = 'image/jpeg'
    
    model = genai.GenerativeModel(Config.IMAGE_EDIT_MODEL)
    
    response = model.generate_content([
        {
            "inline_data": {
                "mime_type": mime_type,
                "data": data
            }
        },
        edit_prompt
    ])
    
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                raw_data = part.inline_data.data
                result_mime = part.inline_data.mime_type or "image/jpeg"
                ext = result_mime.split('/')[-1] if '/' in result_mime else 'jpeg'
                if isinstance(raw_data, str):
                    raw_data = base64.b64decode(raw_data)
                elif not isinstance(raw_data, bytes):
                    raw_data = base64.b64decode(str(raw_data))
                filename = _save_image_bytes(raw_data, ext)
                return f"/static/generated/{filename}"
    
    raise ValueError("No image was returned from the edit API.")
