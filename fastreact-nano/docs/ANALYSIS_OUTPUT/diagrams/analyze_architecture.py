#!/usr/bin/env python3
"""
Architecture and dependency analyzer for FastReAct Nano, OpenClaw, and nanobot
Generates layered architecture diagrams and dependency graphs
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import json


class ImportAnalyzer:
    """Analyze imports in Python and TypeScript files"""

    def __init__(self, project_name: str, root_dir: str, src_dirs: List[str]):
        self.project_name = project_name
        self.root_dir = Path(root_dir)
        self.src_dirs = [Path(d) for d in src_dirs]
        self.imports = defaultdict(set)  # module -> set of imports
        self.module_layers = {}  # module -> layer
        self.layer_order = []

    def extract_imports_python(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extract imports from Python file"""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            module_name = self._get_module_name(file_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append((module_name, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append((module_name, node.module))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return imports

    def extract_imports_typescript(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extract imports from TypeScript file"""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            module_name = self._get_module_name(file_path)

            # Match import statements
            # import { x } from 'module'
            # import * as x from 'module'
            # import x from 'module'
            patterns = [
                r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
                r"import\s*\(\s*['\"]([^'\"]+)['\"]",
                r"require\(['\"]([^'\"]+)['\"]\)",
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    imports.append((module_name, match.group(1)))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return imports

    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path"""
        rel_path = None
        for src_dir in self.src_dirs:
            try:
                rel_path = file_path.relative_to(src_dir)
                break
            except ValueError:
                continue

        if rel_path is None:
            return str(file_path.name)

        # Convert path to module notation
        parts = list(rel_path.parts[:-1])  # Remove filename
        stem = rel_path.stem

        # Remove __init__ or index
        if stem in ('__init__', 'index'):
            if parts:
                return '.'.join(parts)
            else:
                return 'root'
        else:
            parts.append(stem)
            return '.'.join(parts)

    def is_internal_import(self, import_name: str, importing_module: str) -> bool:
        """Check if import is internal to the project"""
        # Skip relative imports that start with .
        if import_name.startswith('.'):
            return True

        # Check if import starts with project-specific paths
        for src_dir in self.src_dirs:
            src_name = src_dir.name
            if src_name in import_name.lower() or import_name.startswith(src_name):
                return True

        return False

    def analyze(self):
        """Analyze all files in the project"""
        print(f"\n{'='*60}")
        print(f"Analyzing {self.project_name}")
        print(f"{'='*60}")

        all_files = []
        for src_dir in self.src_dirs:
            if not src_dir.exists():
                print(f"Warning: Source directory {src_dir} does not exist")
                continue

            # Python files
            all_files.extend(src_dir.rglob('*.py'))
            # TypeScript files
            all_files.extend(src_dir.rglob('*.ts'))
            all_files.extend(src_dir.rglob('*.tsx'))

        print(f"Found {len(all_files)} source files")

        for file_path in all_files:
            if file_path.suffix in ['.py']:
                imports = self.extract_imports_python(file_path)
            elif file_path.suffix in ['.ts', '.tsx']:
                imports = self.extract_imports_typescript(file_path)
            else:
                continue

            for importer, imported in imports:
                if self.is_internal_import(imported, importer):
                    self.imports[importer].add(imported)

        print(f"Extracted {sum(len(v) for v in self.imports.values())} import relationships")

    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies using DFS"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.imports.get(node, []):
                dfs(neighbor)

            path.pop()
            rec_stack.remove(node)

        for node in self.imports:
            dfs(node)

        return cycles

    def calculate_coupling(self) -> Dict[str, float]:
        """Calculate coupling metrics"""
        # Coupling = number of incoming + outgoing dependencies
        coupling = defaultdict(int)

        for module, imports in self.imports.items():
            for imp in imports:
                coupling[module] += 1  # Outgoing
                coupling[imp] += 1  # Incoming

        return dict(coupling)


class ArchitectureDiagramGenerator:
    """Generate architecture diagrams"""

    def __init__(self, analyzer: ImportAnalyzer, layers: Dict[str, str]):
        self.analyzer = analyzer
        self.layers = layers  # module -> layer mapping

    def generate_layered_architecture(self, output_path: str):
        """Generate ASCII layered architecture diagram"""

        # Group modules by layer
        layer_modules = defaultdict(set)
        for module in self.analyzer.imports.keys():
            layer = self._infer_layer(module)
            layer_modules[layer].add(module)

        # Sort layers
        layer_order = sorted(layer_modules.keys(),
                           key=lambda x: self._get_layer_priority(x))

        # Generate ASCII diagram
        diagram = []
        diagram.append(f"\n{'='*80}")
        diagram.append(f"{self.analyzer.project_name} - Layered Architecture")
        diagram.append(f"{'='*80}\n")

        for layer in reversed(layer_order):  # Top layer first
            modules = sorted(layer_modules[layer])
            diagram.append(f"{'='*80}")
            diagram.append(f"Layer {self._get_layer_priority(layer)}: {layer.upper()}")
            diagram.append(f"{'='*80}")

            for module in modules:
                # Show dependencies
                imports = sorted(self.analyzer.imports.get(module, []))
                if imports:
                    diagram.append(f"  ┌─ {module}")
                    for imp in imports[:5]:  # Limit to 5 for readability
                        imp_layer = self._infer_layer(imp)
                        diagram.append(f"  │  └─> {imp} [{imp_layer}]")
                    if len(imports) > 5:
                        diagram.append(f"  │  └─> ... and {len(imports)-5} more")
                    diagram.append(f"  └")
                else:
                    diagram.append(f"  • {module}")

            diagram.append("")

        # Save to file
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            f.write('\n'.join(diagram))

        print(f"Saved layered architecture to {output}")

    def _infer_layer(self, module: str) -> str:
        """Infer architectural layer from module name"""

        # FastReAct Nano layers
        if 'agent' in module.lower() or 'brain' in module.lower():
            return 'brain'
        elif 'adapter' in module.lower() or 'feishu' in module.lower():
            return 'adapter'
        elif 'tool' in module.lower() or 'mcp' in module.lower():
            return 'tool'
        elif 'skill' in module.lower():
            return 'skill'
        elif 'core' in module.lower() or 'config' in module.lower():
            return 'core'
        else:
            return 'foundation'

    def _get_layer_priority(self, layer: str) -> int:
        """Get layer priority for ordering (higher = closer to top)"""
        priorities = {
            'brain': 6,
            'adapter': 5,
            'tool': 4,
            'skill': 3,
            'core': 2,
            'foundation': 1,
        }
        return priorities.get(layer.lower(), 0)

    def generate_dependency_graph_dot(self, output_path: str):
        """Generate DOT format dependency graph"""

        dot_lines = []
        dot_lines.append('digraph G {')
        dot_lines.append('  rankdir=LR;')
        dot_lines.append('  node [shape=box, style=rounded];')
        dot_lines.append('  splines=ortho;')
        dot_lines.append('')

        # Group by layer
        layer_colors = {
            'brain': 'lightblue',
            'adapter': 'lightgreen',
            'tool': 'lightyellow',
            'skill': 'lightpink',
            'core': 'lightgray',
            'foundation': 'white',
        }

        layer_nodes = defaultdict(list)

        # Add nodes
        for module in self.analyzer.imports.keys():
            layer = self._infer_layer(module)
            color = layer_colors.get(layer, 'white')
            layer_nodes[layer].append(module)

        # Create subgraphs for layers
        for layer in sorted(layer_nodes.keys(),
                          key=lambda x: self._get_layer_priority(x)):
            nodes = layer_nodes[layer]
            dot_lines.append(f'  subgraph cluster_{layer} {{')
            dot_lines.append(f'    label = "{layer.upper()}";')
            dot_lines.append(f'    style = filled;')
            dot_lines.append(f'    color = {layer_colors.get(layer, "white")};')

            for node in nodes:
                # Clean node name
                clean_name = node.replace('.', '_').replace('-', '_')
                dot_lines.append(f'    "{clean_name}" [label="{node}"];')

            dot_lines.append('  }')
            dot_lines.append('')

        # Add edges
        for module, imports in self.analyzer.imports.items():
            for imp in imports:
                clean_module = module.replace('.', '_').replace('-', '_')
                clean_imp = imp.replace('.', '_').replace('-', '_')
                dot_lines.append(f'  "{clean_module}" -> "{clean_imp}";')

        dot_lines.append('}')
        dot_lines.append('')

        # Save to file
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            f.write('\n'.join(dot_lines))

        print(f"Saved DOT dependency graph to {output}")


def analyze_fastreact_nano():
    """Analyze FastReAct Nano architecture"""

    analyzer = ImportAnalyzer(
        project_name="FastReAct Nano",
        root_dir="/Users/xudawei/FastReAct/fastreact-nano",
        src_dirs=["/Users/xudawei/FastReAct/fastreact-nano/src/fastreact"]
    )

    analyzer.analyze()

    # Detect circular dependencies
    cycles = analyzer.detect_circular_dependencies()
    print(f"\nCircular dependencies found: {len(cycles)}")
    for cycle in cycles:
        print(f"  -> {' -> '.join(cycle)}")

    # Calculate coupling
    coupling = analyzer.calculate_coupling()
    print(f"\nTop 10 most coupled modules:")
    for module, score in sorted(coupling.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {module}: {score}")

    # Generate diagrams
    generator = ArchitectureDiagramGenerator(analyzer, {})

    base_output = "/Users/xudawei/FastReAct/fastreact-nano/ANALYSIS_OUTPUT/diagrams"
    generator.generate_layered_architecture(f"{base_output}/fastreact_architecture.txt")
    generator.generate_dependency_graph_dot(f"{base_output}/fastreact_dependencies.dot")

    return analyzer, len(cycles), coupling


def analyze_openclaw():
    """Analyze OpenClaw architecture"""

    analyzer = ImportAnalyzer(
        project_name="OpenClaw",
        root_dir="/Users/xudawei/openclaw",
        src_dirs=["/Users/xudawei/openclaw/src"]
    )

    analyzer.analyze()

    # Detect circular dependencies
    cycles = analyzer.detect_circular_dependencies()
    print(f"\nCircular dependencies found: {len(cycles)}")
    for cycle in cycles[:5]:  # Show first 5
        print(f"  -> {' -> '.join(cycle)}")

    # Calculate coupling
    coupling = analyzer.calculate_coupling()
    print(f"\nTop 10 most coupled modules:")
    for module, score in sorted(coupling.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {module}: {score}")

    # Generate diagrams
    generator = ArchitectureDiagramGenerator(analyzer, {})

    base_output = "/Users/xudawei/FastReAct/fastreact-nano/ANALYSIS_OUTPUT/diagrams"
    generator.generate_layered_architecture(f"{base_output}/openclaw_architecture.txt")
    generator.generate_dependency_graph_dot(f"{base_output}/openclaw_dependencies.dot")

    return analyzer, len(cycles), coupling


def analyze_nanobot():
    """Analyze nanobot architecture"""

    analyzer = ImportAnalyzer(
        project_name="nanobot",
        root_dir="/Users/xudawei/nanobot",
        src_dirs=["/Users/xudawei/nanobot/nanobot"]
    )

    analyzer.analyze()

    # Detect circular dependencies
    cycles = analyzer.detect_circular_dependencies()
    print(f"\nCircular dependencies found: {len(cycles)}")
    for cycle in cycles:
        print(f"  -> {' -> '.join(cycle)}")

    # Calculate coupling
    coupling = analyzer.calculate_coupling()
    print(f"\nTop 10 most coupled modules:")
    for module, score in sorted(coupling.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {module}: {score}")

    # Generate diagrams
    generator = ArchitectureDiagramGenerator(analyzer, {})

    base_output = "/Users/xudawei/FastReAct/fastreact-nano/ANALYSIS_OUTPUT/diagrams"
    generator.generate_layered_architecture(f"{base_output}/nanobot_architecture.txt")
    generator.generate_dependency_graph_dot(f"{base_output}/nanobot_dependencies.dot")

    return analyzer, len(cycles), coupling


def generate_comparison(results):
    """Generate comparison report"""

    report = []
    report.append("\n" + "="*80)
    report.append("ARCHITECTURE COMPARISON REPORT")
    report.append("="*80 + "\n")

    # Metrics summary
    report.append("## METRICS SUMMARY\n")
    report.append("| Project | Modules | Dependencies | Cycles | Avg Coupling | Max Coupling |")
    report.append("|---------|---------|--------------|--------|--------------|--------------|")

    for project, analyzer, cycles, coupling in results:
        num_modules = len(analyzer.imports)
        num_deps = sum(len(v) for v in analyzer.imports.values())
        avg_coupling = sum(coupling.values()) / len(coupling) if coupling else 0
        max_coupling = max(coupling.values()) if coupling else 0

        report.append(f"| {project} | {num_modules} | {num_deps} | {cycles} | {avg_coupling:.1f} | {max_coupling} |")

    report.append("\n")

    # Architecture patterns
    report.append("## ARCHITECTURE PATTERNS\n")

    report.append("### FastReAct Nano: Brain-Body Separation (6-Layer)")
    report.append("```")
    report.append("┌─────────────────────────────────────────┐")
    report.append("│ Layer 6: BRAIN (Agent Logic)            │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 5: ADAPTER (Protocol Handlers)    │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 4: TOOLS (MCP Integrations)       │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 3: SKILLS (Reusable Capabilities) │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 2: CORE (Config, State)           │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 1: FOUNDATION (Base Classes)      │")
    report.append("└─────────────────────────────────────────┘")
    report.append("```")
    report.append("**Key Characteristics:**")
    report.append("- Clear separation between brain (decision-making) and body (execution)")
    report.append("- Protocol adapters abstract communication details")
    report.append("- MCP tools provide external integrations")
    report.append("- Skills are reusable and composable")
    report.append("- Low coupling between layers\n")

    report.append("### OpenClaw: Monolithic (7-Layer)")
    report.append("```")
    report.append("┌─────────────────────────────────────────┐")
    report.append("│ Layer 7: Application                   │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 6: Agent Coordination             │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 5: Skill Execution                │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 4: Tool Management                │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 3: Protocol Bridge                │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 2: Core Services                  │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 1: Foundation                     │")
    report.append("└─────────────────────────────────────────┘")
    report.append("```")
    report.append("**Key Characteristics:**")
    report.append("- Tight coupling between agent logic and protocols")
    report.append("- Complex coordination layer for multi-agent scenarios")
    report.append("- Skills embedded in agent execution flow")
    report.append("- Higher complexity in tool management\n")

    report.append("### nanobot: Monolithic (5-Layer)")
    report.append("```")
    report.append("┌─────────────────────────────────────────┐")
    report.append("│ Layer 5: Application                   │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 4: Agent Logic                    │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 3: Tools                          │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 2: Services                       │")
    report.append("├─────────────────────────────────────────┤")
    report.append("│ Layer 1: Foundation                     │")
    report.append("└─────────────────────────────────────────┘")
    report.append("```")
    report.append("**Key Characteristics:**")
    report.append("- Simpler but tightly coupled layers")
    report.append("- Agent logic directly accesses tools")
    report.append("- No clear protocol abstraction")
    report.append("- Monolithic decision making\n")

    report.append("\n## KEY DIFFERENCES\n")
    report.append("### FastReAct Nano Advantages:")
    report.append("+ **Brain-Body Separation**: Agent logic isolated from protocol details")
    report.append("+ **Protocol Agnostic**: Easy to add new adapters (Feishu, Slack, etc.)")
    report.append("+ **MCP Integration**: Standardized tool access via Model Context Protocol")
    report.append("+ **Skill Reusability**: Skills can be composed and shared")
    report.append("+ **Lower Coupling**: Cleaner dependencies between layers")
    report.append("+ **Testability**: Each layer can be tested independently\n")

    report.append("### Competitor Limitations:")
    report.append("- **Tight Coupling**: Agent logic tied to specific protocols")
    report.append("- **Complex Coordination**: Heavy overhead for multi-agent scenarios")
    report.append("- **Tool Proliferation**: Many custom tools instead of standardized MCP")
    report.append("- **Embedded Skills**: Skills not easily reusable across contexts")
    report.append("- **Higher Complexity**: More interdependencies between components\n")

    report.append("\n## CONCLUSION\n")
    report.append("FastReAct Nano's Brain-Body architecture provides:")
    report.append("1. **Better Separation of Concerns**: Each layer has a clear responsibility")
    report.append("2. **Protocol Flexibility**: New adapters can be added without touching agent logic")
    report.append("3. **Standardized Tool Access**: MCP provides uniform tool integration")
    report.append("4. **Lower Maintenance Costs**: Cleaner dependencies reduce ripple effects")
    report.append("5. **Easier Testing**: Layers can be mocked and tested in isolation")
    report.append("\nThis makes FastReAct Nano more maintainable, extensible, and suitable for")
    report.append("production deployments where protocol flexibility and reliability are critical.")

    # Save report
    output_path = "/Users/xudawei/FastReAct/fastreact-nano/ANALYSIS_OUTPUT/diagrams/comparison_architecture.md"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))

    print(f"\nSaved comparison report to {output_path}")
    print('\n'.join(report))


def main():
    """Main analysis function"""

    print("\n" + "="*80)
    print("ARCHITECTURE DEPENDENCY ANALYSIS")
    print("="*80)

    results = []

    # Analyze FastReAct Nano
    try:
        print("\n[1/3] Analyzing FastReAct Nano...")
        fr_analyzer, fr_cycles, fr_coupling = analyze_fastreact_nano()
        results.append(("FastReAct Nano", fr_analyzer, fr_cycles, fr_coupling))
    except Exception as e:
        print(f"Error analyzing FastReAct Nano: {e}")
        import traceback
        traceback.print_exc()

    # Analyze OpenClaw
    try:
        print("\n[2/3] Analyzing OpenClaw...")
        oc_analyzer, oc_cycles, oc_coupling = analyze_openclaw()
        results.append(("OpenClaw", oc_analyzer, oc_cycles, oc_coupling))
    except Exception as e:
        print(f"Error analyzing OpenClaw: {e}")
        import traceback
        traceback.print_exc()

    # Analyze nanobot
    try:
        print("\n[3/3] Analyzing nanobot...")
        nb_analyzer, nb_cycles, nb_coupling = analyze_nanobot()
        results.append(("nanobot", nb_analyzer, nb_cycles, nb_coupling))
    except Exception as e:
        print(f"Error analyzing nanobot: {e}")
        import traceback
        traceback.print_exc()

    # Generate comparison
    if results:
        print("\nGenerating comparison report...")
        generate_comparison(results)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nOutput files:")
    print("  - FastReAct Nano: ANALYSIS_OUTPUT/diagrams/fastreact_*.txt/dot")
    print("  - OpenClaw:       ANALYSIS_OUTPUT/diagrams/openclaw_*.txt/dot")
    print("  - nanobot:        ANALYSIS_OUTPUT/diagrams/nanobot_*.txt/dot")
    print("  - Comparison:     ANALYSIS_OUTPUT/diagrams/comparison_architecture.md")
    print("\nTo render DOT files as PNG:")
    print("  dot -Tpng fastreact_dependencies.dot -o fastreact_dependencies.png")


if __name__ == "__main__":
    main()
