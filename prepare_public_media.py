"""Publish intro media as CDN assets rather than large Python-function responses."""
from pathlib import Path
from shutil import copyfile

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'static/media/auth'
TARGET=ROOT/'public/assets/media/auth'
FILES=('lusion-background.mp4','lusion-poster.jpg','cash_cash_ft_tritonal_-_untouchable_extended_mix.mp3')

def main():
    for name in FILES:
        if not (SOURCE/name).is_file():raise FileNotFoundError('Missing intro asset: '+name)
    TARGET.mkdir(parents=True,exist_ok=True)
    for name in FILES:copyfile(SOURCE/name,TARGET/name)
    print('Prepared intro video, poster and music for Vercel CDN.')

if __name__=='__main__':main()
