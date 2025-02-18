import "../style.css";
import "../Pages/login.css";
import React, { useState } from "react";
import axios from "axios"; // Import Axios for API calls
import qs from 'qs'
import { baseURL } from "../api"; 


const Sign_up = () => {
  const [activeForm, setActiveForm] = useState("signUp");
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Handle input change
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
  
    try {
      if (activeForm === "signIn") {
        // Log the data to check if username and password are not empty
        console.log("Signing in with", { username: formData.username, password: formData.password });
        console.log("Form Data for Sign In:", formData); // Log the formData


        const response = await axios.post(`${baseURL}/auth/token`, qs.stringify({
          username: formData.username,
          password: formData.password,
        }), {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          }
        });
        
  
        if (response.status === 200) {
          setSuccess("Logged in successfully!");
          // Store token or user info in local storage
          localStorage.setItem("token", response.data.token);
          // Redirect or update UI
        }
      } else if (activeForm === "signUp") {
        // Validate password match before making the API call
        if (formData.password !== formData.confirmPassword) {
          setError("Passwords do not match.");
          return;
        }
  
        const response = await axios.post(`${baseURL}/auth/register`, {
          username: formData.username, // Make sure you send 'username' here too
          email: formData.email,
          password: formData.password,
        });
  
        if (response.status === 201) {
          setSuccess("Account created successfully! Please sign in.");
          setActiveForm("signIn");
        }
      }
    } catch (err) {
      // Log error response for better understanding
      console.error("API error:", err.response?.data);
      setError(err.response?.data?.detail?.map(e => e.msg).join(", ") || "An error occurred. Please try again.");
      if (err.response) {
        // The request was made and the server responded with a status code
        setError(err.response.data.message || "An error occurred. Please try again.");
      } else if (err.request) {
        // The request was made but no response was received
        setError("No response from the server. Please check your connection.");
      } else {
        // Something happened in setting up the request
        setError("Error in request setup: " + err.message);
      }
    }
  };

  return (
    <div className="auth-container">
      <h2>Welcome to Buy Via</h2>
      <p>Your ultimate AI-driven price comparison platform</p>
      <div className="form-toggle">
        <button
          className={`toggle-button ${activeForm === "signIn" ? "active" : ""}`}
          onClick={() => setActiveForm("signIn")}
        >
          Sign In
        </button>
        <button
          className={`toggle-button ${activeForm === "signUp" ? "active" : ""}`}
          onClick={() => setActiveForm("signUp")}
        >
          Sign Up
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}
      {success && <p className="success-message">{success}</p>}

      {activeForm === "signIn" && (
        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            type="username"
            name="username"
            placeholder="Email"
            value={formData.username}
            onChange={handleInputChange}
            required
          />
          <input
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleInputChange}
            required
          />
          <button type="submit" className="form-submit">Sign In</button>
        </form>
      )}

      {activeForm === "signUp" && (
        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            type="text"
            name="username"
            placeholder="Username"
            value={formData.username}
            onChange={handleInputChange}
            required
          />
          <input
            type="email"
            name="email"
            placeholder="Email"
            value={formData.email}
            onChange={handleInputChange}
            required
          />
          <input
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleInputChange}
            required
          />
          <input
            type="password"
            name="confirmPassword"
            placeholder="Confirm Password"
            value={formData.confirmPassword}
            onChange={handleInputChange}
            required
          />
          <button type="submit" className="form-submit">Sign Up</button>
        </form>
      )}
    </div>
  );
};

export default Sign_up;
