/* $OpenBSD$ */

/*
 * Copyright (c) 2024 Thomas Adam <thomas@xteddy.org>
 *
 * Permission to use, copy, modify, and distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF MIND, USE, DATA OR PROFITS, WHETHER
 * IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING
 * OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

#ifdef HAVE_LIBPNG

#include <sys/types.h>

#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include <png.h>

#include "tmux.h"

/*
 * Load a PNG file with alpha channel and convert it to a sixel_image.
 *
 * pw, ph: target pixel dimensions; 0 means use the image's natural size.
 * If only one dimension is given (the other is 0), the missing dimension is
 * computed from the image's aspect ratio.
 *
 * Returns NULL on error and sets *errp to a descriptive string.
 */
struct sixel_image *
image_load_png(const char *path, u_int pw, u_int ph,
    u_int xpixel, u_int ypixel, const char **errp)
{
	FILE		   *fp;
	png_structp	    png;
	png_infop	    info;
	u_int		    w, h, y, dx, dy, sx, sy;
	/* volatile: these are modified after setjmp; must survive longjmp. */
	volatile u_int	    tw, th;
	u_char		  **rows, *rgba, *scaled;
	struct sixel_image *si;
	int		    bit_depth, color_type;

	tw = pw;
	th = ph;

	*errp = NULL;

	fp = fopen(path, "rb");
	if (fp == NULL) {
		*errp = strerror(errno);
		return (NULL);
	}

	png = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	if (png == NULL) {
		*errp = "png_create_read_struct failed";
		fclose(fp);
		return (NULL);
	}

	info = png_create_info_struct(png);
	if (info == NULL) {
		*errp = "png_create_info_struct failed";
		png_destroy_read_struct(&png, NULL, NULL);
		fclose(fp);
		return (NULL);
	}

	if (setjmp(png_jmpbuf(png))) {
		*errp = "PNG decode error";
		png_destroy_read_struct(&png, &info, NULL);
		fclose(fp);
		return (NULL);
	}

	png_init_io(png, fp);
	png_read_info(png, info);

	w          = png_get_image_width(png, info);
	h          = png_get_image_height(png, info);
	bit_depth  = png_get_bit_depth(png, info);
	color_type = png_get_color_type(png, info);

	/* Normalise to RGBA 8-bit. */
	if (color_type == PNG_COLOR_TYPE_PALETTE)
		png_set_palette_to_rgb(png);
	if (color_type == PNG_COLOR_TYPE_GRAY && bit_depth < 8)
		png_set_expand_gray_1_2_4_to_8(png);
	if (png_get_valid(png, info, PNG_INFO_tRNS))
		png_set_tRNS_to_alpha(png);
	if (bit_depth == 16)
		png_set_strip_16(png);
	if (color_type == PNG_COLOR_TYPE_GRAY ||
	    color_type == PNG_COLOR_TYPE_GRAY_ALPHA)
		png_set_gray_to_rgb(png);
	/* Add alpha channel for non-alpha colour types. */
	if (color_type == PNG_COLOR_TYPE_RGB ||
	    color_type == PNG_COLOR_TYPE_GRAY ||
	    color_type == PNG_COLOR_TYPE_PALETTE)
		png_set_filler(png, 0xff, PNG_FILLER_AFTER);

	png_read_update_info(png, info);

	rgba = xmalloc((size_t)w * h * 4);
	rows = xmalloc(h * sizeof *rows);
	for (y = 0; y < h; y++)
		rows[y] = rgba + y * w * 4;

	png_read_image(png, (png_bytepp)rows);
	png_read_end(png, NULL);
	png_destroy_read_struct(&png, &info, NULL);
	fclose(fp);
	free(rows);

	/* Resolve a partial target size from the image's aspect ratio. */
	if (tw == 0 && th > 0 && h > 0)
		tw = th * w / h;
	else if (th == 0 && tw > 0 && w > 0)
		th = tw * h / w;

	if (tw > 0 && th > 0 && (tw != w || th != h)) {
		scaled = xmalloc((size_t)tw * th * 4);
		for (dy = 0; dy < th; dy++) {
			sy = dy * h / th;
			for (dx = 0; dx < tw; dx++) {
				sx = dx * w / tw;
				memcpy(scaled + (dy * tw + dx) * 4,
				    rgba + (sy * w + sx) * 4, 4);
			}
		}
		free(rgba);
		si = sixel_from_rgba(scaled, tw, th, xpixel, ypixel);
		free(scaled);
	} else {
		si = sixel_from_rgba(rgba, w, h, xpixel, ypixel);
		free(rgba);
	}

	if (si == NULL)
		*errp = "sixel encode failed";
	return (si);
}

#endif /* HAVE_LIBPNG */
