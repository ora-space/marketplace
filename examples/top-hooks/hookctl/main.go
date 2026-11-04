// Command hookctl installs and removes one bundled Claude Code plugin
// marketplace through the user's Claude Code CLI.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const commandTimeout = 100 * time.Second

type integration struct {
	Marketplace string `json:"marketplace"`
	Plugin      string `json:"plugin"`
	Identifier  string `json:"identifier"`
}

type installedPlugin struct {
	ID string `json:"id"`
}

// main dispatches the single lifecycle command requested by the Hook manifest.
func main() {
	if len(os.Args) != 2 {
		fail("usage: hookctl install|uninstall")
	}
	if os.Args[1] != "install" && os.Args[1] != "uninstall" {
		fail("usage: hookctl install|uninstall")
	}

	assets, err := assetDirectory()
	if err != nil {
		fail(err.Error())
	}
	config, err := loadIntegration(assets)
	if err != nil {
		fail(err.Error())
	}
	marketplace := filepath.Join(assets, "claude-marketplace")
	if !inside(assets, marketplace) {
		fail("bundled marketplace path escapes the plugin assets directory")
	}

	claude, err := findClaude()
	if err != nil {
		fail(err.Error())
	}
	runner := &claudeRunner{binary: claude}

	switch os.Args[1] {
	case "install":
		err = install(runner, config, marketplace)
	case "uninstall":
		err = uninstall(runner, config)
	}
	if err != nil {
		fail(err.Error())
	}
}

// fail prints one diagnostic line and exits non-zero so the host records a
// visible lifecycle failure without rolling back the installed package.
func fail(message string) {
	fmt.Fprintln(os.Stderr, "top-hooks:", message)
	os.Exit(1)
}

// assetDirectory resolves the assets directory containing this executable.
func assetDirectory() (string, error) {
	executable, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("resolve hookctl executable: %w", err)
	}
	resolved, err := filepath.EvalSymlinks(executable)
	if err == nil {
		executable = resolved
	}
	return filepath.Dir(executable), nil
}

// loadIntegration reads the package-specific marketplace and plugin names.
func loadIntegration(assets string) (integration, error) {
	var config integration
	source, err := os.ReadFile(filepath.Join(assets, "integration.json"))
	if err != nil {
		return config, fmt.Errorf("read integration.json: %w", err)
	}
	if err := json.Unmarshal(source, &config); err != nil {
		return config, fmt.Errorf("parse integration.json: %w", err)
	}
	if config.Marketplace == "" || config.Plugin == "" || config.Identifier == "" {
		return config, errors.New("integration.json must name a marketplace, plugin and identifier")
	}
	return config, nil
}

// inside reports whether child stays below parent after lexical cleaning.
func inside(parent, child string) bool {
	relative, err := filepath.Rel(filepath.Clean(parent), filepath.Clean(child))
	return err == nil && relative != ".." && !strings.HasPrefix(relative, ".."+string(filepath.Separator))
}

// findClaude locates the Claude Code CLI, honoring CLAUDE_BIN for tests and
// unusual installations.
func findClaude() (string, error) {
	if configured := os.Getenv("CLAUDE_BIN"); configured != "" {
		info, err := os.Stat(configured)
		if err != nil || info.IsDir() {
			return "", fmt.Errorf("CLAUDE_BIN does not name an executable file: %s", configured)
		}
		return configured, nil
	}
	for _, name := range []string{"claude", "claude.exe"} {
		path, err := exec.LookPath(name)
		if err == nil {
			return path, nil
		}
	}
	return "", errors.New("Claude Code CLI was not found on PATH; install Claude Code or set CLAUDE_BIN")
}

// install replaces any previous copy of this package's marketplace and then
// installs the plugin at user scope.
func install(runner *claudeRunner, config integration, marketplace string) error {
	pluginID := config.Plugin + "@" + config.Marketplace
	if _, err := os.Stat(filepath.Join(marketplace, ".claude-plugin", "marketplace.json")); err != nil {
		return fmt.Errorf("bundled marketplace is missing: %w", err)
	}

	// A previous init may have left the same local marketplace registered.
	// Remove it first so add/install always use this package's exact directory,
	// including after an Ora package update.
	if installed, err := runner.pluginInstalled(pluginID); err != nil {
		return err
	} else if installed {
		if _, err := runner.run("plugin", "uninstall", pluginID, "--scope", "user", "--yes", "--json"); err != nil {
			return fmt.Errorf("remove previous %s: %w", pluginID, err)
		}
	}
	if present, err := runner.marketplacePresent(config.Marketplace); err != nil {
		return err
	} else if present {
		if _, err := runner.run("plugin", "marketplace", "remove", config.Marketplace, "--scope", "user", "--json"); err != nil {
			return fmt.Errorf("remove previous marketplace %s: %w", config.Marketplace, err)
		}
	}
	if _, err := runner.run("plugin", "marketplace", "add", marketplace, "--scope", "user", "--json"); err != nil {
		return fmt.Errorf("add bundled Claude marketplace: %w", err)
	}
	if _, err := runner.run("plugin", "install", pluginID, "--scope", "user", "--yes", "--json"); err != nil {
		return fmt.Errorf("install %s: %w", pluginID, err)
	}
	installed, err := runner.pluginInstalled(pluginID)
	if err != nil {
		return err
	}
	if !installed {
		return fmt.Errorf("Claude Code reported success but %s is not installed", pluginID)
	}
	fmt.Printf("top-hooks: installed %s\n", pluginID)
	return nil
}

// uninstall removes the plugin and its package-local marketplace. Cleanup is
// best-effort per command, then verified so a broken Claude home is visible.
func uninstall(runner *claudeRunner, config integration) error {
	pluginID := config.Plugin + "@" + config.Marketplace
	installed, err := runner.pluginInstalled(pluginID)
	if err != nil {
		return err
	}
	var uninstallOutput string
	if installed {
		uninstallOutput, err = runner.run("plugin", "uninstall", pluginID, "--scope", "user", "--yes", "--json")
		if err != nil {
			return fmt.Errorf("remove %s: %w: %s", pluginID, err, uninstallOutput)
		}
	}
	present, err := runner.marketplacePresent(config.Marketplace)
	if err != nil {
		return err
	}
	var removeOutput string
	if present {
		removeOutput, err = runner.run("plugin", "marketplace", "remove", config.Marketplace, "--scope", "user", "--json")
		if err != nil {
			return fmt.Errorf("remove marketplace %s: %w: %s", config.Marketplace, err, removeOutput)
		}
	}
	fmt.Printf("top-hooks: uninstalled %s\n", pluginID)
	return nil
}

type claudeRunner struct {
	binary string
}

// run executes one Claude CLI command and returns combined diagnostics.
func (runner *claudeRunner) run(arguments ...string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), commandTimeout)
	defer cancel()

	command := exec.CommandContext(ctx, runner.binary, arguments...)
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	err := command.Run()
	diagnostic := strings.TrimSpace(stdout.String())
	if message := strings.TrimSpace(stderr.String()); message != "" {
		diagnostic += "\n" + message
	}
	if ctx.Err() == context.DeadlineExceeded {
		return diagnostic, errors.New("Claude Code CLI timed out")
	}
	if err != nil {
		return diagnostic, err
	}
	return diagnostic, nil
}

// output runs one read-only command and returns stdout for JSON parsing.
func (runner *claudeRunner) output(arguments ...string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(context.Background(), commandTimeout)
	defer cancel()

	command := exec.CommandContext(ctx, runner.binary, arguments...)
	var stderr bytes.Buffer
	command.Stderr = &stderr
	output, err := command.Output()
	if ctx.Err() == context.DeadlineExceeded {
		return nil, errors.New("Claude Code CLI timed out")
	}
	if err != nil {
		message := strings.TrimSpace(stderr.String())
		if message == "" {
			message = err.Error()
		}
		return nil, errors.New(message)
	}
	return output, nil
}

// pluginInstalled checks the user-scope plugin inventory by ID.
func (runner *claudeRunner) pluginInstalled(pluginID string) (bool, error) {
	output, err := runner.output("plugin", "list", "--json")
	if err != nil {
		return false, fmt.Errorf("list Claude plugins: %w", err)
	}
	var plugins []installedPlugin
	if err := json.Unmarshal(output, &plugins); err != nil {
		return false, fmt.Errorf("parse Claude plugin list: %w", err)
	}
	for _, plugin := range plugins {
		if plugin.ID == pluginID {
			return true, nil
		}
	}
	return false, nil
}

// marketplacePresent checks the user-scope marketplace inventory by name.
func (runner *claudeRunner) marketplacePresent(name string) (bool, error) {
	output, err := runner.output("plugin", "marketplace", "list", "--json")
	if err != nil {
		return false, fmt.Errorf("list Claude marketplaces: %w", err)
	}
	var marketplaces []struct {
		Name string `json:"name"`
	}
	if err := json.Unmarshal(output, &marketplaces); err != nil {
		var keyed map[string]json.RawMessage
		if keyedErr := json.Unmarshal(output, &keyed); keyedErr != nil {
			return false, fmt.Errorf("parse Claude marketplace list: %w", err)
		}
		_, present := keyed[name]
		return present, nil
	}
	for _, marketplace := range marketplaces {
		if marketplace.Name == name {
			return true, nil
		}
	}
	return false, nil
}
