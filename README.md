# Simple-SESH-Summary
Generates a simple HTML page from your Spotify extended streaming history just by telling it where the directory is.

Example page [mbektic.com/SESH](https://mbektic.com/SESH/)

## Before you start
 - If you want to get a copy of your Spotify extended streaming history, you can get it [HERE](https://www.spotify.com/us/account/privacy/)
 - I wrote this using python 3.13.5, but any recent version of python _should_ work.


## Running
- Double click `GenerateHTMLSummary.py` or run the script via terminal using `python.exe .\GenerateHTMLSummary.py`  
  - A gui like the one below will pop up. 
  - ![Image](https://github.com/user-attachments/assets/6f19e6db-54f3-40c5-a444-b5f4f0c2bbfe)
  - Click browse and select the folder that contains your extracted JSON files.
  - After altering the settings to your liking, click "Generate Summary"
  - It will take a few seconds to generate the report, you can see the progress with the progress bar.
  - ![Image](https://github.com/user-attachments/assets/2b06553c-8a3a-4cec-8f26-cab54e7c10ba)
  - You should get a confirmation screen like so, clicking "Open Report" _should_ open it in your web browser.
  - ![Image](https://github.com/user-attachments/assets/9804fe5d-7e23-4a8d-a02e-528ede041b65)
  - The file will have generated in the same folder as the script if you wish to revisit it later.
  - After opening the page, you can switch between playtime and play count as well as theme by clicking the settings button at the top right of the page.
    - ![Image](https://github.com/user-attachments/assets/569ae55d-8d09-4141-bbbb-4539b9c6b3dc)
- If you wish to change the default settings, they are found in the `config.py` file.
  - You can also run the script like so `python.exe .\GenerateHTMLSummary.py --skip-gui`
  - It will skip the GUI and just generate the report with the values in `config.py`
    - You will need to set the default directory in the `config.py`.

### Minimum Year filter (optional)
You can optionally filter out any plays before a specified year. This is useful if you only want to analyze recent listening history.

- In the GUI:
  - Check "Filter out plays before this year" in the "Minimum Year (optional)" section.
  - Enter a year (e.g., 2020). Valid range is 1900–3000. If the field is empty or invalid, you’ll be prompted to fix it.

- In `config.py` (when using `--skip-gui` or setting defaults):
  - Set `MIN_YEAR` to an integer (e.g., `MIN_YEAR = 2020`) to enable filtering.
  - Set `MIN_YEAR = None` to disable filtering (default).
  - Any invalid value or out‑of‑range year will automatically disable the filter during validation.

What gets filtered:
- All processing steps ignore entries whose timestamp year is less than `MIN_YEAR`.
- This applies to all statistics and also to the "On This Day" section.

### Compression (if you run into an issue with the generated HTML file)
In `config.py` there is a flag set `COMPRESS_TABLE_DATA = True`.
If you are experiencing issues with the generated HTML file, you can try setting this to `False`.



## IMPORTANT NOTES
- When you first open the HTML page, it can take a few seconds to load depending on how many years of history you have.
  - For example, with 10 years of history mine sometimes takes 2–3 seconds. 
- The resulting `.html` file can be shared without any of the other scripts or style files as everything is all built into it.
- None of your data ever leaves your system or is uploaded anywhere, this all stays on your machine.

## Features
### Time Filter Selector
This will filter the tables based on the year selected.
#### Desktop
![Image](https://github.com/user-attachments/assets/61c6785a-ef91-4398-881f-796b6af98d53)
#### Mobile
![Image](https://github.com/user-attachments/assets/f3b2b1fa-f7f0-4479-a888-46783e4a38c3)
#### Selecting Custom
By selecting custom, you can select any date range for the tables.
![Image](https://github.com/user-attachments/assets/ea59f1b3-c270-4f83-8e59-126eee50f318)

### Artist (Dark Mode and Play Time)
![Image](https://github.com/user-attachments/assets/a2b84762-d564-44f0-90c4-3235670fb64a)

### Tracks (Light Mode and Play Count)
You can also click on any track here to open it on Spotify.
![Image](https://github.com/user-attachments/assets/bbbd23b6-c7c8-4b19-b337-a13b8dc346fc)

### Albums (Search)
![Image](https://github.com/user-attachments/assets/1a9ba192-1fc5-4cc6-b115-a5f57ebef6db)

### Personality Type
![Image](https://github.com/user-attachments/assets/a18a3ea2-279a-494e-bcf5-97989c344841)

### Stats
#### Per Artis Stats
##### Total Per Year
![Image](https://github.com/user-attachments/assets/767f796c-61c1-487c-955c-84e2e2454423)
##### Over the years
![Image](https://github.com/user-attachments/assets/9b9e8716-a416-4982-9d24-4e1e3cbb7127)
##### Change over Years
![Image](https://github.com/user-attachments/assets/6176b642-c3d0-4ad9-a6cc-aed4d9d24471)
#### Overview & Time/Library 
![Image](https://github.com/user-attachments/assets/fcac2f11-4e1b-4e4d-be34-a0673d5e634c)
#### Milestones/Popularity
![Image](https://github.com/user-attachments/assets/c849a630-78e1-43d4-8fa7-7dda20969c7b)
#### Patters/Session & Behavior
![Image](https://github.com/user-attachments/assets/ff73754e-2461-4261-9d91-f4af2a06c42e)
#### On this day
You can also click on any track here to open it on Spotify.
![Image](https://github.com/user-attachments/assets/84f50afd-3810-445c-9679-7686b589aa2b)
#### Artist played every year
![Image](https://github.com/user-attachments/assets/bfa47186-ae50-4c73-a2b4-77e7fdf0b0db)
#### Listening By Year
![Image](https://github.com/user-attachments/assets/96da5c9c-930f-4649-b779-fcb2206db750)
### Smart Playlists
You can also click on any track here to open it on Spotify.
![Image](https://github.com/user-attachments/assets/09505297-bcd4-4df3-8088-995f8a77bc09)
#### Heatmap
![Image](https://github.com/user-attachments/assets/169be638-f73d-48ea-9dfb-43dd055e9b31)

## Thanks
 - [Tippy.js](https://atomiks.github.io/tippyjs/)
 - [Popper.js](https://popper.js.org/docs/)