import React, { useState } from "react";
import { auth } from "../firebase";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
} from "firebase/auth";

type AuthModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const commonPassword = "brll-skill-arcade-password"; // This password must be at least 6 characters long for Firebase.

  if (!isOpen) return null;

  const handleAuthAction = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await signInWithEmailAndPassword(auth, email, commonPassword);
      onClose(); // Close modal on successful login
    } catch (signInError: any) {
      // If the user does not exist, create a new account.
      if (
        signInError.code === "auth/user-not-found" ||
        signInError.code === "auth/invalid-credential"
      ) {
        try {
          await createUserWithEmailAndPassword(auth, email, commonPassword);
          onClose(); // Close modal on successful sign-up
        } catch (signUpError: any) {
          setError(signUpError.message);
        }
      } else {
        // For other sign-in errors (e.g., invalid email), display the error.
        setError(signInError.message);
      }
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 px-6 py-6 rounded-xl shadow-xl w-full max-w-sm">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Login</h2>
          <button
            onClick={onClose}
            className="text-xl text-gray-400 hover:text-white"
          >
            &times;
          </button>
        </div>

        {error && (
          <p className="bg-red-500 text-white text-sm p-2 rounded-xl mb-4">
            {error}
          </p>
        )}

        <form onSubmit={handleAuthAction}>
          <div className="mb-4">
            <label
              className="block text-gray-400 text-sm font-bold mb-2"
              htmlFor="email"
            >
              Email
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="shadow appearance-none border rounded-xl w-full py-2 px-3 bg-gray-700 text-white leading-tight focus:outline-none focus:shadow-outline"
              required
              placeholder="Enter your email"
            />
          </div>
          <div className="flex items-center justify-center">
            <button
              type="submit"
              className="bg-green-500 hover:bg-green-400 text-white font-bold py-2 px-4 rounded-xl focus:outline-none focus:shadow-outline"
            >
              Continue
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AuthModal;
