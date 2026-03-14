import { useState, useEffect, useRef } from 'react';
import { patientsApi } from '@/lib/api';

export interface UsePDFViewerReturn {
  fileUrl: string | null;
  isLoading: boolean;
  error: string | null;
  numPages: number;
  currentPage: number;
  scale: number;
  setNumPages: (n: number) => void;
  goToPage: (page: number) => void;
  goToPrev: () => void;
  goToNext: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;
}

export function usePDFViewer(patientId: string, initialPage = 1): UsePDFViewerReturn {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [scale, setScale] = useState(1.0);
  const objectUrlRef = useRef<string | null>(null);

  // Load PDF blob when patientId changes
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    setFileUrl(null);

    patientsApi.downloadOriginalPdf(patientId)
      .then((blob) => {
        if (cancelled) return;
        // Revoke previous blob URL to avoid memory leaks
        if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;
        setFileUrl(url);
      })
      .catch(() => {
        if (!cancelled) setError('No se pudo cargar el PDF de la historia clínica.');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [patientId]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, []);

  // Sync currentPage when initialPage changes (e.g. clicking a page reference)
  useEffect(() => {
    setCurrentPage(initialPage);
  }, [initialPage]);

  const goToPage = (page: number) => {
    if (!isNaN(page) && page >= 1 && page <= numPages) setCurrentPage(page);
  };
  const goToPrev = () => setCurrentPage((p) => Math.max(1, p - 1));
  const goToNext = () => setCurrentPage((p) => Math.min(numPages, p + 1));
  const zoomIn = () => setScale((s) => Math.min(3.0, parseFloat((s + 0.25).toFixed(2))));
  const zoomOut = () => setScale((s) => Math.max(0.5, parseFloat((s - 0.25).toFixed(2))));
  const resetZoom = () => setScale(1.0);

  return {
    fileUrl,
    isLoading,
    error,
    numPages,
    setNumPages,
    currentPage,
    scale,
    goToPage,
    goToPrev,
    goToNext,
    zoomIn,
    zoomOut,
    resetZoom,
  };
}
