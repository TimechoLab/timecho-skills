#!/bin/bash
# TsFile build and setup script for all supported languages

set -e

echo "🚀 TsFile Multi-Language Build Script"
echo "======================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Java version
check_java() {
    if command_exists java; then
        java_version=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d'.' -f1-2)
        echo "✅ Java found: $java_version"
        if [[ $java_version < "1.8" ]]; then
            echo "❌ Java 1.8 or higher required"
            return 1
        fi
    else
        echo "❌ Java not found"
        return 1
    fi
}

# Function to check Maven
check_maven() {
    if command_exists mvn; then
        mvn_version=$(mvn --version | head -n1 | awk '{print $3}')
        echo "✅ Maven found: $mvn_version"
    else
        echo "❌ Maven not found"
        return 1
    fi
}

# Function to check C++ build tools
check_cpp() {
    local missing_tools=()

    if ! command_exists cmake; then
        missing_tools+=("cmake")
    fi

    if ! command_exists make; then
        missing_tools+=("make")
    fi

    if ! command_exists g++; then
        missing_tools+=("g++")
    fi

    if [ ${#missing_tools[@]} -eq 0 ]; then
        echo "✅ C++ build tools found"
        return 0
    else
        echo "❌ Missing C++ tools: ${missing_tools[*]}"
        echo "   Install with: sudo apt-get install ${missing_tools[*]} libuuid-dev"
        return 1
    fi
}

# Function to check Python
check_python() {
    if command_exists python3; then
        python_version=$(python3 --version | awk '{print $2}')
        echo "✅ Python found: $python_version"
    else
        echo "❌ Python3 not found"
        return 1
    fi
}

# Main build function
build_tsfile() {
    local lang="$1"

    case $lang in
        "java")
            echo "📦 Building Java TsFile..."
            mvn clean package -P with-java -DskipTests
            echo "✅ Java build completed"
            ;;

        "cpp")
            echo "📦 Building C++ TsFile..."
            check_cpp || return 1
            mvn clean package -P with-cpp -DskipTests
            echo "✅ C++ build completed"
            ;;

        "python")
            echo "📦 Building Python TsFile..."
            check_cpp || return 1
            mvn clean package -P with-cpp,with-python -DskipTests
            echo "✅ Python build completed"
            ;;

        "all")
            echo "📦 Building all TsFile languages..."
            check_cpp || return 1
            mvn clean package -P with-java,with-cpp,with-python -DskipTests
            echo "✅ All builds completed"
            ;;

        *)
            echo "❌ Unknown language: $lang"
            echo "Available options: java, cpp, python, all"
            return 1
            ;;
    esac
}

# Function to install locally
install_tsfile() {
    local lang="$1"

    case $lang in
        "java")
            echo "📦 Installing Java TsFile locally..."
            mvn install -P with-java -DskipTests
            echo "✅ Java installed to local repository"
            ;;

        "all")
            echo "📦 Installing all TsFile languages locally..."
            mvn install -P with-java,with-cpp,with-python -DskipTests
            echo "✅ All languages installed to local repository"
            ;;

        *)
            echo "❌ Local install only supported for: java, all"
            return 1
            ;;
    esac
}

# Function to run tests
test_tsfile() {
    local lang="$1"

    case $lang in
        "java")
            echo "🧪 Running Java tests..."
            mvn test -P with-java
            ;;

        "cpp")
            echo "🧪 Running C++ tests..."
            mvn test -P with-cpp
            ;;

        "python")
            echo "🧪 Running Python tests..."
            mvn test -P with-python
            ;;

        "all")
            echo "🧪 Running all tests..."
            mvn test -P with-java,with-cpp,with-python
            ;;

        *)
            echo "❌ Unknown test target: $lang"
            return 1
            ;;
    esac
}

# Function to show usage
show_usage() {
    cat << EOF
TsFile Multi-Language Build Script

Usage: $0 <command> [language]

Commands:
  check               Check prerequisites for all languages
  build <lang>        Build TsFile for specific language or 'all'
  install <lang>      Install TsFile to local Maven repository
  test <lang>         Run tests for specific language or 'all'
  clean              Clean all build artifacts

Languages:
  java               Java implementation
  cpp                C++ implementation
  python             Python implementation (requires C++)
  all                All implementations

Examples:
  $0 check           Check all prerequisites
  $0 build java      Build only Java version
  $0 build all       Build all versions
  $0 install java    Install Java version locally
  $0 test all        Run all tests
  $0 clean          Clean build artifacts

Prerequisites:
  Java:   Java 1.8+, Maven 3.6.3+
  C++:    cmake, make, g++, clang-format, libuuid-dev
  Python: Python 3.x, C++ prerequisites
EOF
}

# Main script logic
case "${1:-}" in
    "check")
        echo "🔍 Checking prerequisites..."
        check_java
        check_maven
        check_cpp
        check_python
        echo "✅ Prerequisites check completed"
        ;;

    "build")
        if [ -z "${2:-}" ]; then
            echo "❌ Language required for build command"
            show_usage
            exit 1
        fi
        check_java || exit 1
        check_maven || exit 1
        build_tsfile "$2"
        ;;

    "install")
        if [ -z "${2:-}" ]; then
            echo "❌ Language required for install command"
            show_usage
            exit 1
        fi
        check_java || exit 1
        check_maven || exit 1
        install_tsfile "$2"
        ;;

    "test")
        if [ -z "${2:-}" ]; then
            echo "❌ Language required for test command"
            show_usage
            exit 1
        fi
        check_java || exit 1
        check_maven || exit 1
        test_tsfile "$2"
        ;;

    "clean")
        echo "🧹 Cleaning build artifacts..."
        mvn clean
        echo "✅ Clean completed"
        ;;

    *)
        show_usage
        exit 1
        ;;
esac