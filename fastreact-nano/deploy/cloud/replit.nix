# Replit Configuration for FastReAct Nano
# This file configures the Replit development environment

{ pkgs }: {
  # Required dependencies
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
  ];

  # Environment variables
  env = {
    PYTHON_VERSION = "3.11";
    PYTHONPATH = "${pkgs.python311}/${pkgs.python311.sitePackages}";
  };
}
