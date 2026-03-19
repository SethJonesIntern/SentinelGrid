import React from "react";
import { Navigate } from "react-router-dom";
import { getUser } from "../lib/auth";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = getUser();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}