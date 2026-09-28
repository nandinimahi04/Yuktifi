"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function Error({
 error,
 reset,
}: {
 error: Error & { digest?: string };
 reset: () => void;
}) {
 useEffect(() => {
 // Log the error to an error reporting service
 console.error("YuktiFi App Route Error: ", error);
 }, [error]);

 return (
 <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
 <div className="max-w-md w-full bg-warm-surface p-8 rounded-xl shadow-lg border border-red-100 text-center space-y-4">
 <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
 <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
 </svg>
 </div>
 <h2 className="text-2xl font-bold text-slate-900">Something went wrong!</h2>
 <div className="bg-slate-100 p-4 rounded text-left text-sm font-sans text-red-600 overflow-auto max-h-48 break-words">
 {error.message ||"Unknown error occurred"}
 </div>
 <Button
 onClick={
 // Attempt to recover by trying to re-render the segment
 () => reset()
 }
 className="w-full mt-4"
 >
 Try again
 </Button>
 </div>
 </div>
 );
}
