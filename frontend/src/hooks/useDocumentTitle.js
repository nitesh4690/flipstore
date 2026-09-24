import { useEffect } from "react";

/** Sets document.title for a page and restores the previous title on unmount. */
export default function useDocumentTitle(title) {
  useEffect(() => {
    const previous = document.title;
    document.title = title ? `${title} · FlipStore` : "FlipStore — Modern E-Commerce";
    return () => {
      document.title = previous;
    };
  }, [title]);
}
