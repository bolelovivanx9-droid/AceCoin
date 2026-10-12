
from io import BytesIO
from pathlib import Path
import unicodedata

from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from pilmoji import Pilmoji
except ImportError:
    Pilmoji = None


WIDTH = 1100
HEIGHT = 600

GOLD = (232, 190, 92)
LIGHT_GOLD = (255, 225, 150)
DARK_GOLD = (130, 88, 28)
WHITE = (245, 242, 232)
MUTED = (166, 163, 155)
PANEL = (25, 24, 29, 235)

FRAME_STYLES = {
    "frame_bronze": {
        "color": (176, 111, 57),
        "inner": (100, 65, 39),
        "width": 3,
    },
    "frame_silver": {
        "color": (192, 205, 220),
        "inner": (100, 113, 130),
        "width": 4,
    },
    "frame_gold": {
        "color": (255, 194, 55),
        "inner": (145, 101, 25),
        "width": 5,
    },
    "frame_diamond": {
        "color": (100, 225, 255),
        "inner": (65, 135, 180),
        "width": 5,
    },
    "frame_cosmic": {
        "color": (190, 105, 255),
        "inner": (90, 45, 155),
        "width": 6,
    },
    "frame_neon": {
        "color": (0, 245, 255),
        "inner": (190, 70, 255),
        "width": 5,
    },
}

FONT_REGULAR = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

FONT_BOLD = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

FONT_EMOJI = [
    "C:/Windows/Fonts/seguiemj.ttf",
    "C:/Windows/Fonts/seguisym.ttf",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf",
]


def load_font(size, bold=False):
    candidates = FONT_BOLD if bold else FONT_REGULAR

    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except (OSError, ValueError):
                continue

    return ImageFont.load_default()


def load_emoji_font(size):
    for path in FONT_EMOJI:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except (OSError, ValueError):
                continue

    return load_font(size)


def is_emoji_cluster(text):
    for char in text:
        code = ord(char)

        if (
            code >= 0x1F000
            or 0x2600 <= code <= 0x27BF
            or 0xFE00 <= code <= 0xFE0F
            or 0x1F3FB <= code <= 0x1F3FF
            or code == 0x200D
        ):
            return True

    return False


def split_text_clusters(text):
    """Не разрывает составные эмодзи при обработке имени."""
    clusters = []
    current = ""

    for char in text:
        if not current:
            current = char
        elif (
            unicodedata.combining(char)
            or char in ("\ufe0e", "\ufe0f", "\u200d")
            or current.endswith("\u200d")
            or 0x1F3FB <= ord(char) <= 0x1F3FF
        ):
            current += char
        else:
            clusters.append(current)
            current = char

    if current:
        clusters.append(current)

    return clusters


def cluster_font(cluster, size, regular_font):
    if is_emoji_cluster(cluster):
        return load_emoji_font(size)

    return regular_font


def cluster_width(draw, cluster, font):
    try:
        return draw.textlength(cluster, font=font)
    except (AttributeError, TypeError, ValueError):
        bbox = draw.textbbox((0, 0), cluster, font=font)
        return bbox[2] - bbox[0]


def fit_rich_text(draw, text, regular_font, size, max_width):
    """Ограничивает длину текста, сохраняя целые эмодзи."""
    clusters = split_text_clusters(text)
    result = []
    current_width = 0

    ellipsis = "…"
    ellipsis_width = cluster_width(draw, ellipsis, regular_font)
    truncated = False

    for cluster in clusters:
        font = cluster_font(cluster, size, regular_font)
        width = cluster_width(draw, cluster, font)

        if current_width + width > max_width - ellipsis_width:
            truncated = True
            break

        result.append(cluster)
        current_width += width

    if truncated:
        result.append(ellipsis)

    return "".join(result)


def draw_rich_text(image, position, text, regular_font, fill, size):
    """Рисует текст с поддержкой цветных эмодзи через Pilmoji."""
    if Pilmoji is not None:
        try:
            with Pilmoji(image) as pilmoji:
                pilmoji.text(
                    position,
                    text,
                    font=regular_font,
                    fill=fill,
                )
            return
        except Exception:
            pass

    draw = ImageDraw.Draw(image)
    x, y = position

    for cluster in split_text_clusters(text):
        font = cluster_font(cluster, size, regular_font)

        try:
            draw.text(
                (x, y),
                cluster,
                font=font,
                fill=fill,
            )
        except (OSError, ValueError):
            draw.text(
                (x, y),
                "?",
                font=regular_font,
                fill=fill,
            )

        x += cluster_width(draw, cluster, font)


def draw_centered_text(draw, center_x, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    draw.text(
        (center_x - text_width / 2, y),
        text,
        font=font,
        fill=fill,
    )


def draw_card_frame(image, frame_id):
    """Рисует выбранную косметическую рамку карточки."""
    style = FRAME_STYLES.get(frame_id)

    if not style:
        return

    color = style["color"]
    inner = style["inner"]
    width = style["width"]

    # Неоновое свечение для секретной рамки.
    if frame_id == "frame_neon":
        glow = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 0),
        )

        glow_draw = ImageDraw.Draw(glow)

        glow_draw.rounded_rectangle(
            (8, 8, WIDTH - 8, HEIGHT - 8),
            radius=34,
            outline=(*color, 220),
            width=14,
        )

        glow_draw.rounded_rectangle(
            (36, 36, WIDTH - 36, HEIGHT - 36),
            radius=23,
            outline=(*inner, 190),
            width=8,
        )

        glow = glow.filter(
            ImageFilter.GaussianBlur(16)
        )

        image.alpha_composite(glow)

    # Чёткие линии рамки поверх свечения.
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (8, 8, WIDTH - 8, HEIGHT - 8),
        radius=34,
        outline=color,
        width=width,
    )

    draw.rounded_rectangle(
        (36, 36, WIDTH - 36, HEIGHT - 36),
        radius=23,
        outline=inner,
        width=2,
    )

    # Декоративные уголки.
    corner = 48

    for x, direction_x in (
        (22, 1),
        (WIDTH - 22, -1),
    ):
        for y, direction_y in (
            (22, 1),
            (HEIGHT - 22, -1),
        ):
            draw.line(
                (
                    x,
                    y,
                    x + corner * direction_x,
                    y,
                ),
                fill=color,
                width=2,
            )

            draw.line(
                (
                    x,
                    y,
                    x,
                    y + corner * direction_y,
                ),
                fill=color,
                width=2,
            )


def create_avatar(image, avatar_bytes, first_name):
    """Создаёт круглую аватарку с рамкой."""
    avatar_x, avatar_y = 78, 190
    avatar_size = 148

    avatar = None

    if avatar_bytes:
        try:
            avatar = Image.open(
                BytesIO(avatar_bytes)
            ).convert("RGBA")

            side = min(avatar.size)
            left = (avatar.width - side) // 2
            top = (avatar.height - side) // 2

            avatar = avatar.crop(
                (left, top, left + side, top + side)
            )

            avatar = avatar.resize(
                (avatar_size, avatar_size),
                Image.Resampling.LANCZOS,
            )
        except (OSError, ValueError):
            avatar = None

    if avatar is None:
        avatar = Image.new(
            "RGBA",
            (avatar_size, avatar_size),
            (35, 30, 22, 255),
        )

        avatar_draw = ImageDraw.Draw(avatar)
        safe_name = (first_name or "A").strip() or "A"
        initial = safe_name[0].upper()
        initial_font = load_font(64, True)

        bbox = avatar_draw.textbbox(
            (0, 0),
            initial,
            font=initial_font,
        )

        initial_width = bbox[2] - bbox[0]
        initial_height = bbox[3] - bbox[1]

        avatar_draw.text(
            (
                (avatar_size - initial_width) / 2 - bbox[0],
                (avatar_size - initial_height) / 2 - bbox[1],
            ),
            initial,
            font=initial_font,
            fill=LIGHT_GOLD,
        )

    mask = Image.new("L", (avatar_size, avatar_size), 0)

    ImageDraw.Draw(mask).ellipse(
        (0, 0, avatar_size - 1, avatar_size - 1),
        fill=255,
    )

    image.paste(avatar, (avatar_x, avatar_y), mask)

    draw = ImageDraw.Draw(image)

    draw.ellipse(
        (
            avatar_x - 4,
            avatar_y - 4,
            avatar_x + avatar_size + 4,
            avatar_y + avatar_size + 4,
        ),
        outline=GOLD,
        width=4,
    )


def draw_progress_bar(draw, x, y, width, height, progress):
    """Рисует полосу прогресса от 0 до 100 процентов."""
    progress = max(0.0, min(1.0, progress))

    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=height // 2,
        fill=(48, 44, 38),
        outline=(105, 81, 42),
        width=1,
    )

    filled_width = int(width * progress)

    if filled_width > 0:
        draw.rounded_rectangle(
            (
                x,
                y,
                x + max(filled_width, height),
                y + height,
            ),
            radius=height // 2,
            fill=GOLD,
        )


def generate_profile_card(
    first_name: str,
    username: str,
    user_id: int,
    balance: int,
    avatar_bytes: bytes = None,
    level: int = 1,
    rank: str = "Bronze",
    rank_emoji: str = "🥉",
    xp: int = 0,
    xp_in_level: int = 0,
    xp_per_level: int = 100,
    frame_id: str = None,
    title: str = None,
) -> BytesIO:
    """Создаёт карточку профиля с поддержкой косметики магазина."""

    image = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (12, 12, 16, 255),
    )

    draw = ImageDraw.Draw(image)

    # Фоновый градиент.
    for y in range(HEIGHT):
        ratio = y / HEIGHT

        color = (
            int(20 - ratio * 9),
            int(19 - ratio * 8),
            int(25 - ratio * 10),
            255,
        )

        draw.line((0, y, WIDTH, y), fill=color)

    # Мягкое золотое свечение справа.
    glow = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0),
    )

    glow_draw = ImageDraw.Draw(glow)

    for radius in range(240, 0, -4):
        alpha = max(1, int(2 * (1 - radius / 240)))

        glow_draw.ellipse(
            (
                865 - radius,
                280 - radius,
                865 + radius,
                280 + radius,
            ),
            fill=(218, 165, 55, alpha),
        )

    glow = glow.filter(ImageFilter.GaussianBlur(35))
    image = Image.alpha_composite(image, glow)
    draw = ImageDraw.Draw(image)

    # Базовая рамка.
    draw.rounded_rectangle(
        (18, 18, WIDTH - 18, HEIGHT - 18),
        radius=30,
        outline=DARK_GOLD,
        width=3,
    )

    draw.rounded_rectangle(
        (29, 29, WIDTH - 29, HEIGHT - 29),
        radius=24,
        outline=(78, 61, 35),
        width=1,
    )

    # Заголовок.
    draw.text(
        (65, 48),
        "ACECOIN",
        font=load_font(34, True),
        fill=LIGHT_GOLD,
    )

    draw.text(
        (67, 91),
        "CASINO  /  PLAYER PROFILE",
        font=load_font(16),
        fill=MUTED,
    )

    draw.text(
        (WIDTH - 255, 59),
        "PLAYER CARD",
        font=load_font(17, True),
        fill=GOLD,
    )

    draw.line(
        (65, 130, WIDTH - 65, 130),
        fill=DARK_GOLD,
        width=2,
    )

    # Аватар.
    create_avatar(image, avatar_bytes, first_name)
    draw = ImageDraw.Draw(image)

    # Имя игрока.
    safe_name = (first_name or "Игрок").strip() or "Игрок"
    name_font = load_font(34, True)

    display_name = fit_rich_text(
        draw,
        safe_name,
        name_font,
        34,
        475,
    )

    draw_rich_text(
        image,
        (260, 178),
        display_name,
        name_font,
        WHITE,
        34,
    )

    draw = ImageDraw.Draw(image)

    # Username.
    clean_username = (username or "").strip().lstrip("@")

    display_username = (
        f"@{clean_username}"
        if clean_username and clean_username != "unknown"
        else "@username не указан"
    )

    username_font = load_font(20)

    while (
        draw.textbbox(
            (0, 0),
            display_username,
            font=username_font,
        )[2] > 475
        and len(display_username) > 1
    ):
        display_username = display_username[:-2] + "…"

    draw.text(
        (263, 224),
        display_username,
        font=username_font,
        fill=MUTED,
    )

    draw.text(
        (263, 265),
        f"PLAYER ID: {user_id}",
        font=load_font(17),
        fill=GOLD,
    )

    # Ранг и уровень.
    draw.rounded_rectangle(
        (258, 302, 720, 350),
        radius=12,
        fill=(37, 32, 25, 235),
        outline=DARK_GOLD,
        width=1,
    )

    draw_rich_text(
        image,
        (274, 312),
        f"{rank_emoji} {rank.upper()}",
        load_font(20, True),
        LIGHT_GOLD,
        20,
    )

    draw = ImageDraw.Draw(image)

    draw.text(
        (515, 314),
        f"LEVEL {max(1, int(level))}",
        font=load_font(20, True),
        fill=WHITE,
    )

    # Титул из магазина.
    if title:
        title_font = load_font(19, True)

        title_text = fit_rich_text(
            draw,
            f"✦ {title} ✦",
            title_font,
            19,
            475,
        )

        draw_rich_text(
            image,
            (260, 355),
            title_text,
            title_font,
            LIGHT_GOLD,
            19,
        )

    # XP и прогресс уровня.
    xp_per_level = max(1, int(xp_per_level))
    xp_in_level = max(0, min(int(xp_in_level), xp_per_level))
    xp = max(0, int(xp))

    xp_y = 395 if title else 370

    draw.text(
        (260, xp_y),
        f"EXPERIENCE  /  {xp:,} XP".replace(",", " "),
        font=load_font(18, True),
        fill=WHITE,
    )

    draw.text(
        (735, xp_y),
        f"{xp_in_level}/{xp_per_level}",
        font=load_font(17, True),
        fill=GOLD,
    )

    draw_progress_bar(
        draw,
        260,
        xp_y + 31,
        505,
        13,
        xp_in_level / xp_per_level,
    )

    remaining_xp = xp_per_level - xp_in_level

    draw.text(
        (260, xp_y + 55),
        f"До следующего уровня: {remaining_xp} XP",
        font=load_font(16),
        fill=MUTED,
    )

    # Нижняя панель баланса.
    draw.rounded_rectangle(
        (65, 470, 750, 535),
        radius=15,
        fill=PANEL,
        outline=(95, 73, 38),
        width=1,
    )

    draw.text(
        (85, 488),
        "BALANCE",
        font=load_font(17, True),
        fill=MUTED,
    )

    balance_text = f"{max(0, int(balance)):,}".replace(",", " ")
    balance_font = load_font(30, True)

    draw.text(
        (245, 481),
        balance_text,
        font=balance_font,
        fill=LIGHT_GOLD,
    )

    balance_bbox = draw.textbbox(
        (245, 481),
        balance_text,
        font=balance_font,
    )

    draw.text(
        (balance_bbox[2] + 12, 490),
        "$",
        font=load_font(24, True),
        fill=GOLD,
    )

    # Эмблема справа.
    emblem_x, emblem_y = 900, 275

    draw.ellipse(
        (
            emblem_x - 100,
            emblem_y - 100,
            emblem_x + 100,
            emblem_y + 100,
        ),
        outline=DARK_GOLD,
        width=3,
    )

    draw.ellipse(
        (
            emblem_x - 86,
            emblem_y - 86,
            emblem_x + 86,
            emblem_y + 86,
        ),
        outline=GOLD,
        width=2,
    )

    draw.ellipse(
        (
            emblem_x - 72,
            emblem_y - 72,
            emblem_x + 72,
            emblem_y + 72,
        ),
        outline=(78, 61, 35),
        width=1,
    )

    emblem_font = load_font(56, True)
    emblem = "AC"

    emblem_bbox = draw.textbbox(
        (0, 0),
        emblem,
        font=emblem_font,
    )

    draw.text(
        (
            emblem_x
            - (emblem_bbox[2] - emblem_bbox[0]) / 2
            - emblem_bbox[0],
            emblem_y
            - (emblem_bbox[3] - emblem_bbox[1]) / 2
            - emblem_bbox[1],
        ),
        emblem,
        font=emblem_font,
        fill=LIGHT_GOLD,
    )

    draw_centered_text(
        draw,
        emblem_x,
        emblem_y + 118,
        "EST. ACECOIN",
        load_font(15, True),
        MUTED,
    )

    draw.text(
        (WIDTH - 310, HEIGHT - 57),
        "THE GAME IS YOURS",
        font=load_font(16, True),
        fill=GOLD,
    )

    # Накладываем рамку магазина поверх карточки.
    draw_card_frame(image, frame_id)

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG")
    output.seek(0)
    output.name = "acecoin_profile.png"

    return output
