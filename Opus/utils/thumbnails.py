import random
import logging
import os
import re
import traceback
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch

logging.basicConfig(level=logging.INFO)


def changeImageSize(maxWidth, maxHeight, image):
    """Resize image while maintaining aspect ratio."""
    try:
        widthRatio = maxWidth / image.size[0]
        heightRatio = maxHeight / image.size[1]
        newWidth = int(widthRatio * image.size[0])
        newHeight = int(heightRatio * image.size[1])
        return image.resize((newWidth, newHeight))
    except Exception as e:
        logging.error(f"Error resizing image: {e}")
        return image


def truncate(text):
    """Truncate text to fit within defined space."""
    list_words = text.split(" ")
    text1, text2 = "", ""

    for word in list_words:
        if len(text1) + len(word) < 30:
            text1 += " " + word
        elif len(text2) + len(word) < 30:
            text2 += " " + word

    return [text1.strip(), text2.strip()]


def random_color():
    """Generate a random RGB color."""
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def generate_gradient(width, height, colors):
    """Generate a smooth multi-color gradient background."""
    try:
        base = Image.new('RGBA', (width, height), colors[0])
        for i in range(1, len(colors)):
            overlay = Image.new('RGBA', (width, height), colors[i])
            mask = Image.new('L', (width, height))
            mask_data = [int(255 * (y / height)) for y in range(height) for _ in range(width)]
            mask.putdata(mask_data)
            base.paste(overlay, (0, 0), mask)

        return base.resize((width, height))  # Ensure gradient matches required size
    except Exception as e:
        logging.error(f"Error generating gradient: {e}")
        return Image.new("RGBA", (width, height), (0, 0, 0, 255))


def add_border(image, border_width, border_color):
    """Add a border around the image."""
    try:
        new_size = (image.size[0] + 2 * border_width, image.size[1] + 2 * border_width)
        new_image = Image.new("RGBA", new_size, border_color)
        new_image.paste(image, (border_width, border_width))
        return new_image
    except Exception as e:
        logging.error(f"Error adding border: {e}")
        return image


async def get_thumb(videoid: str):
    """Fetch YouTube video thumbnail and generate an enhanced image."""
    try:
        if os.path.isfile(f"cache/{videoid}_v4.png"):
            return f"cache/{videoid}_v4.png"

        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1)

        # Fetch video metadata
        for result in (await results.next())["result"]:
            title = result.get("title", "Unknown Title")
            title = re.sub(r"\W+", " ", title).title()
            duration = result.get("duration", "Live")
            thumbnail = result.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
            views = result.get("viewCount", {}).get("short", "Unknown Views")
            channel = result.get("channel", {}).get("name", "Unknown Channel")

        # Download thumbnail
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    filepath = f"cache/thumb{videoid}.png"
                    async with aiofiles.open(filepath, mode="wb") as f:
                        await f.write(await resp.read())
                else:
                    logging.error(f"Failed to fetch thumbnail for {videoid}, HTTP {resp.status}")
                    return None

        youtube = Image.open(filepath).convert("RGBA")
        youtube = changeImageSize(400, 225, youtube)

        # Create blurred background
        background = youtube.filter(ImageFilter.BoxBlur(50))
        background = ImageEnhance.Brightness(background).enhance(0.6)

        # Generate multi-color gradient
        gradient_image = generate_gradient(1280, 720, [random_color(), random_color(), random_color()])
        gradient_image = gradient_image.resize(background.size)  # Ensure correct size
        background = Image.blend(background, gradient_image, alpha=0.3)

        draw = ImageDraw.Draw(background)
        title_font = ImageFont.truetype("Opus/assets/font3.ttf", 45)
        arial = ImageFont.truetype("Opus/assets/font2.ttf", 30)

        # Add Thumbnail to the left
        square_thumbnail = youtube.resize((400, 400))
        background.paste(square_thumbnail, (120, 160), square_thumbnail)

        # Add Text Information
        text_x_position = 565
        title1 = truncate(title)
        draw.text((text_x_position, 180), title1[0], font=title_font, fill=(255, 255, 255))
        draw.text((text_x_position, 230), title1[1], font=title_font, fill=(255, 255, 255))
        draw.text((text_x_position, 320), f"{channel}  |  {views[:23]}", font=arial, fill=(255, 255, 255))

        # Draw progress bar
        line_length = 580
        if duration != "Live":
            color_line_percentage = random.uniform(0.15, 0.85)
            color_line_length = int(line_length * color_line_percentage)
            white_line_length = line_length - color_line_length

            draw.line([(text_x_position, 380), (text_x_position + color_line_length, 380)], fill=(255, 255, 255), width=9)
            draw.line([(text_x_position + color_line_length, 380), (text_x_position + line_length, 380)], fill="white", width=8)
            draw.ellipse([(text_x_position + color_line_length - 10, 370), (text_x_position + color_line_length + 10, 390)], fill=(255, 255, 255))
        else:
            draw.line([(text_x_position, 380), (text_x_position + line_length, 380)], fill=(255, 255, 255), width=9)
            draw.ellipse([(text_x_position + line_length - 10, 370), (text_x_position + line_length + 10, 390)], fill=(255, 255, 255))

        draw.text((text_x_position, 400), "00:00", font=arial, fill=(255, 255, 255))
        draw.text((1080, 400), duration, font=arial, fill=(255, 255, 255))

        # Load Play Button
        play_icon = Image.open("Opus/resources/new.png").resize((580, 62))
        background.paste(play_icon, (text_x_position, 450), play_icon)

        # Save Final Image
        os.remove(filepath)
        final_path = f"cache/{videoid}_v4.png"
        background.save(final_path)

        return final_path

    except Exception as e:
        logging.error(f"Error generating thumbnail for {videoid}: {e}")
        traceback.print_exc()
        return None
