import React,{useEffect, useRef, useState} from "react";
import{createPortal} from "react-dom";

interface DropdownProps{
  value: string;
  onChange: (value: string) => void;
  options: { label: string; value: string }[];
  placeholder?: string;
  style?: React.CSSProperties;
}

export default function Dropdown({ value, onChange, options, placeholder = "Select...", style }: DropdownProps){
  const [open, setOpen] = useState(false);
  const [rect, setRect]= useState<DOMRect | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(()=>{
    function handleClick(e: MouseEvent){
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return ()=> document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    if (!open) return;
    function handleScroll(e: Event) {
      if (listRef.current && listRef.current.contains(e.target as Node)) return;
      setOpen(false);
    }
    function handleResize() {
      if (btnRef.current) setRect(btnRef.current.getBoundingClientRect());
    }
    window.addEventListener("scroll", handleScroll, true);
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("resize", handleResize);
    };
  }, [open]);

  function handleOpen(){
    if (btnRef.current) setRect(btnRef.current.getBoundingClientRect());
    setOpen((v) => !v);
  }
  const selected= options.find((o) => o.value === value);
  return(
    <div ref={ref} style={{ position: "relative", minWidth: 240, ...style }}>
      <button
        ref={btnRef}
        type="button"
        onClick={handleOpen}
        style={{
          width: "100%",
          padding: "8px 28px 8px 12px",
          borderRadius: 9,
          border: open ? "1px solid rgba(59,130,246,0.5)" : "1px solid rgba(255,255,255,0.08)",
          background: "rgba(255,255,255,0.03)",
          color: selected && selected.value !== "" ? "#e2e8f4" : "#6b7a99",
          fontSize: 12,
          fontFamily: "'Space Mono', monospace",
          cursor: "pointer",
          textAlign: "left",
          outline: "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {selected ? selected.label : placeholder}
        </span>
        <svg
          width="10" height="10" viewBox="0 0 10 10"
          style={{ flexShrink: 0, transition: "transform 0.15s", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          <path fill="#6b7a99" d="M5 7L0 2h10z" />
        </svg>
      </button>
      {open&&rect&&createPortal(
        <div
          ref={listRef}
          onMouseDown={(e) => e.stopPropagation()}
          style={{
            position: "fixed",
            top: rect.bottom + 4,
            left: rect.left,
            width: rect.width,
            zIndex: 99,
            background: "#0a1428",
            border: "1px solid rgba(59,130,246,0.25)",
            borderRadius: 9,
            overflow: "hidden",
            boxShadow: "0 8px 32px rgba(0,0,0,0.7)",
            maxHeight: 260,
            overflowY: "auto",
          }}
        >
          {options.map((opt) => (
            <div
              key={opt.value}
              onMouseDown={() => { onChange(opt.value); setOpen(false); }}
              style={{
                padding: "8px 12px",
                fontSize: 12,
                fontFamily: "'Space Mono', monospace",
                color: opt.value === value ? "#93c5fd" : "#c8d3e8",
                background: opt.value === value ? "rgba(59,130,246,0.12)" : "transparent",
                cursor: "pointer",
                borderBottom: "1px solid rgba(255,255,255,0.03)",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(59,130,246,0.08)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = opt.value === value ? "rgba(59,130,246,0.12)" : "transparent")}
            >
              {opt.label}
            </div>
          ))}
        </div>,
        document.body
      )}
    </div>
  );
}
