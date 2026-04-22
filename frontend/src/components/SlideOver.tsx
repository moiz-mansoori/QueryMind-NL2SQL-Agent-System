"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

interface SlideOverProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export default function SlideOver({ isOpen, onClose, title, children }: SlideOverProps) {
  const [isRendered, setIsRendered] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setIsRendered(true);
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
      const timer = setTimeout(() => setIsRendered(false), 300);
      return () => clearTimeout(timer);
    }
    return () => {
      document.body.style.overflow = "auto";
    };
  }, [isOpen]);

  if (!isRendered && !isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className={`fixed inset-0 bg-black/60 backdrop-blur-sm z-50 transition-opacity duration-300 ${isOpen ? "opacity-100" : "opacity-0"}`}
        onClick={onClose}
      />

      {/* Panel */}
      <div 
        className={`fixed inset-y-0 right-0 w-full max-w-xl bg-[#0A0A0F] border-l border-[#1E1E2E] z-50 shadow-2xl transform transition-transform duration-300 ease-in-out flex flex-col ${isOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E1E2E]">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <button 
            onClick={onClose}
            className="p-2 -mr-2 text-[#8888A0] hover:text-white rounded-lg hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          {children}
        </div>
      </div>
    </>
  );
}
