import { useEffect, useRef, useState } from "react";
import { es } from "@/lib/i18n";
import { activeSectionIndex } from "./activeSection";

const links = es.classificationGuide.sectionLinks;

export function useGuideSection() {
  const ref = useRef<HTMLDivElement>(null);
  const [activeId, setActiveId] = useState<string>(links[0].id);

  useEffect(() => {
    const guide = ref.current;
    const scroller = guide?.closest("main");
    if (!guide || !scroller) return;
    const headings = links.map((link) => guide.querySelector<HTMLElement>(`#${link.id}`));
    function update() {
      if (!scroller) return;
      const readingLine = scroller.getBoundingClientRect().top + Math.min(120, scroller.clientHeight * 0.25);
      const atBottom = scroller.scrollHeight > scroller.clientHeight &&
        scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 2;
      const index = activeSectionIndex(headings.map((heading) => heading?.getBoundingClientRect().top ?? Infinity), readingLine, atBottom);
      setActiveId(links[index]?.id ?? links[0].id);
    }
    const frame = requestAnimationFrame(update);
    scroller.addEventListener("scroll", update, { passive: true });
    guide.addEventListener("toggle", update, true);
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      scroller.removeEventListener("scroll", update);
      guide.removeEventListener("toggle", update, true);
      window.removeEventListener("resize", update);
    };
  }, []);

  return { ref, activeId, setActiveId };
}
