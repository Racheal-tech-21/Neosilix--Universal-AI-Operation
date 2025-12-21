// /lib/fetchTechNews.ts
import Parser from "rss-parser";

const parser = new Parser();

export const fetchTechNews = async () => {
  try {
    const feed = await parser.parseURL("https://techcrunch.com/feed/");
    // Return the first 5 headlines
    return feed.items.slice(0, 5).map(item => ({
      title: item.title,
      link: item.link
    }));
  } catch (err) {
    console.error("Failed to fetch tech news:", err);
    return [];
  }
};
