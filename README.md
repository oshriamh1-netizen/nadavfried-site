# nadavfried.co.il

האתר של נדב פריד · תכנון וייעוץ פיננסי.

- **עריכת כתבות:** https://nadavfried.co.il/admin
- **כתובות לקישורים פנימיים:** https://nadavfried.co.il/admin/links.html

## איך זה בנוי
- `site/` — העמודים הקבועים של האתר (דף הבית, מי אני, התהליך וכו').
- `content/articles/` — כל כתבה היא קובץ אחד. נערך דרך /admin.
- `data/categories.json` — רשימת הקטגוריות (נערכת דרך /admin → הגדרות).
- `uploads/` — תמונות שהועלו דרך העורך.
- `templates/article.html` — העיצוב של עמוד כתבה.
- `build.py` — רץ ב-Netlify בכל שינוי: בונה את עמודי הכתבות, עמוד המאמרים, הקרוסלה בדף הבית, sitemap.xml ו-robots.txt לתוך `dist/`.
