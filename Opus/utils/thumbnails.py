import random
import logging
import os
import re
import aiofiles
import aiohttp
import traceback
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch

logging.basicConfig(level=logging.INFO)

def changeImageSize(maxWidth, maxHeight, image):
    return image.resize((maxWidth, maxHeight), Image.LANCZOS)

def truncate(text):
    words = text.split(" ")
    text1, text2 = "", ""
    for word in words:
        if len(text1) + len(word) < 30:
            text1 += " " + word
        elif len(text2) + len(word) < 30:
            text2 += " " + word
    return [text1.strip(), text2.strip()]

def random_color():
    return (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))

def generate_gradient(width, height, colors):
    base = Image.new('RGBA', (width, height), colors[0])
    for i in range(1, len(colors)):
        overlay = Image.new('RGBA', (width, height), colors[i])
        mask = Image.new('L', (width, height))
        mask_data = [int(255 * (y / height)) for y in range(height) for _ in range(width)]
        mask.putdata(mask_data)
        base.paste(overlay, (0, 0), mask)
    return base.resize((width, height), Image.LANCZOS)  # Ensure correct size

def add_border(image, border_width, border_color):
    width, height = image.size
    new_width = width + 2 * border_width
    new_height = height + 2 * border_width
    new_image = Image.new("RGBA", (new_width, new_height), border_color)
    new_image.paste(image, (border_width, border_width))
    return new_image

def crop_center_square(img, output_size, corner_radius=40, crop_scale=1.5):
    half_width, half_height = img.size[0] / 2, img.size[1] / 2
    larger_size = int(output_size * crop_scale)
    img = img.crop((half_width - larger_size / 2, half_height - larger_size / 2, 
                    half_width + larger_size / 2, half_height + larger_size / 2))
    img = img.resize((output_size, output_size))

    mask = Image.new('L', (output_size, output_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, output_size, output_size), corner_radius, fill=255)

    result = Image.new('RGBA', (output_size, output_size))
    result.paste(img, (0, 0), mask)
    return result

def draw_text_with_shadow(background, draw, position, text, font, fill, shadow_offset=(3, 3), shadow_blur=5):
    shadow = Image.new('RGBA', background.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.text(position, text, font=font, fill="black")
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
    background.paste(shadow, shadow_offset, shadow)
    draw.text(position, text, font=font, fill=fill)

async def get_thumb(videoid: str):
    try:
        thumb_path = f"cache/{videoid}_v4.png"
        if os.path.isfile(thumb_path):
            return thumb_path

        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1)
        video_data = (await results.next())["result"][0]

        title = re.sub("\W+", " ", video_data.get("title", "Unsupported Title")).title()
        duration = video_data.get("duration", "Live")
        thumbnail_url = video_data["thumbnails"][0]["url"].split("?")[0] if video_data.get("thumbnails") else None
        views = video_data.get("viewCount", {}).get("short", "Unknown Views")
        channel = video_data.get("channel", {}).get("name", "Unknown Channel")

        if not thumbnail_url:
            logging.error("No thumbnail found for the video.")
            return None

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as resp:
                if resp.status != 200:
                    logging.error(f"Failed to fetch thumbnail: {resp.status}")
                    return None
                content_type = resp.headers.get('Content-Type', '')
                extension = 'jpg' if 'jpeg' in content_type or 'jpg' in content_type else 'png'
                temp_thumb_path = f"cache/thumb{videoid}.{extension}"
                async with aiofiles.open(temp_thumb_path, "wb") as f:
                    await f.write(await resp.read())

        youtube = Image.open(temp_thumb_path).convert("RGBA")
        image1 = changeImageSize(400, 225, youtube)

        background = image1.filter(ImageFilter.BoxBlur(10))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.6)

        gradient_colors = [random_color(), random_color(), random_color()]
        gradient_image = generate_gradient(1280, 720, gradient_colors)
        background = Image.blend(background.resize((1280, 720)), gradient_image, alpha=0.3)

        draw = ImageDraw.Draw(background)
        title_font = ImageFont.truetype("Opus/assets/font3.ttf", 45)
        arial = ImageFont.truetype("Opus/assets/font2.ttf", 30)

        square_thumbnail = crop_center_square(youtube, 400)
        background.paste(square_thumbnail, (120, 160), square_thumbnail)

        title1 = truncate(title)
        draw_text_with_shadow(background, draw, (565, 180), title1[0], title_font, (255, 255, 255))
        draw_text_with_shadow(background, draw, (565, 230), title1[1], title_font, (255, 255, 255))
        draw_text_with_shadow(background, draw, (565, 320), f"{channel}  |  {views[:23]}", arial, (255, 255, 255))

        line_length, line_color = 580, (255, 255, 255)
        #line_length = 580
        #line_color = LinearSegmentedColormap.from_list("blue_to_white", [(0, 0, 1), (1, 1, 1)])

        if duration != "Live":
            color_line_percentage = random.uniform(0.15, 0.85)
            color_line_length = int(line_length * color_line_percentage)

            draw.line([(565, 380), (565 + color_line_length, 380)], fill=line_color, width=9)
            draw.line([(565 + color_line_length, 380), (565 + line_length, 380)], fill="white", width=8)
            draw.ellipse([(565 + color_line_length - 10, 370), (565 + color_line_length + 10, 390)], fill=line_color)
        else:
            draw.line([(565, 380), (565 + line_length, 380)], fill=line_color, width=9)
            draw.ellipse([(1145, 370), (1165, 390)], fill=line_color)

        draw_text_with_shadow(background, draw, (565, 400), "00:00", arial, (255, 255, 255))
        draw_text_with_shadow(background, draw, (1080, 400), duration, arial, (255, 255, 255))

        play_icons = Image.open("Opus/resources/new.png").resize((580, 62))
        background.paste(play_icons, (565, 450), play_icons)

        os.remove(temp_thumb_path)
        background.save(thumb_path)

        return thumb_path

    except Exception as e:
        logging.error(f"Error generating thumbnail for video {videoid}: {e}")
        traceback.print_exc()
        return None
