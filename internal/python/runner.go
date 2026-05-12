package python

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"Stock_Intelligence_Dashboard/internal/utils"
)

type PythonRunner interface {
	RunDbCommand(command, arg string) ([]byte, error)
	RunDbCommandWithOptions(command, arg string, options map[string]string) ([]byte, error)
	RunScore(momentum, volume, sentiment float64) ([]byte, error)
}

type DefaultPythonRunner struct{}

func (p *DefaultPythonRunner) RunDbCommand(command, arg string) ([]byte, error) {
	return p.RunDbCommandWithOptions(command, arg, map[string]string{})
}

func (p *DefaultPythonRunner) RunDbCommandWithOptions(command, arg string, options map[string]string) ([]byte, error) {
	pythonExe := p.getPythonExecutable()
	scriptPath := filepath.Join(utils.GetRootPath(), "src", "api", "db_cli.py")
	args := []string{scriptPath, command}
	if strings.TrimSpace(arg) != "" {
		args = append(args, arg)
	}
	for key, value := range options {
		if strings.TrimSpace(value) == "" {
			continue
		}
		args = append(args, "--"+key, value)
	}
	cmd := exec.Command(pythonExe, args...)
	cmd.Env = os.Environ()
	return cmd.Output()
}

func (p *DefaultPythonRunner) RunScore(momentum, volume, sentiment float64) ([]byte, error) {
	pythonExe := p.getPythonExecutable()
	scriptPath := filepath.Join(utils.GetRootPath(), "src", "ml", "cli.py")
	cmd := exec.Command(pythonExe, scriptPath,
		"--momentum", fmt.Sprintf("%f", momentum),
		"--volume", fmt.Sprintf("%f", volume),
		"--sentiment", fmt.Sprintf("%f", sentiment),
	)
	cmd.Env = os.Environ()
	return cmd.Output()
}

func (p *DefaultPythonRunner) getPythonExecutable() string {
	pythonExe := utils.GetEnv("PYTHON_EXECUTABLE", "")
	if pythonExe != "" {
		return pythonExe
	}

	venvPath := filepath.Join(utils.GetRootPath(), ".venv", "Scripts", "python.exe")
	if _, err := os.Stat(venvPath); err == nil {
		return venvPath
	}
	return "python"
}
