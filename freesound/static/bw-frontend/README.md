# Freesound Beast Whoosh Front end

## Installation
Simply run `npm install` in the root directory of the freesound repo.

## How to run
In order to see one of the pages developed, run:
```
npm start
```

You will be prompted the choose which page to start (use the arrow keys to pick your choice).
Once you select, open the browser at `http://localhost:1234` in order to see that page

## Things temporaly missing
The migration to parcel as bundler temporarily broke some features that had already been developed: no worries, they'll be back as soon as possible! I'm just adding things back based on their priority.
Notable things missing:
- audio player
- there's no "build" mode, i.e. the assets can only be accessed through the dev server run through `npm start` and can't be exported nor optimized
- styleguide: the previous version has been dismissed as it was running react components that were adapted from the html page I added to the dev pages. The plan is to write a very simple in-house styleguide once things get more stable, so to show the different use cases of the UI components/atoms.

## Icons
This project uses https://icomoon.io for generating the icon font.
To import the font project in your own icomon account (a free one is enough), import the file `bw-icons/selection.json`, as explained in the `bw-icons/Read Me.txt` file.
