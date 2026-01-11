"""Specialized ADK Agent Implementations

Concrete implementations of ADK agents for specific tasks:
- Development (code generation)
- Code Review
- Testing
- Documentation
- Research
"""

from typing import Any, Dict, List, Optional

from agents.adk.base import ADKAgent, ADKConfig, ADKResult


class DevelopmentADKAgent(ADKAgent):
    """Agent specialized in code development and generation."""
    
    def get_agent_type(self) -> str:
        return "development"
    
    def get_system_prompt(self) -> str:
        return """You are an expert software developer with deep expertise across multiple programming languages and frameworks.

Your responsibilities:
1. Write clean, efficient, and well-documented code
2. Follow best practices and design patterns
3. Implement proper error handling and input validation
4. Write code that is testable and maintainable
5. Consider edge cases and potential issues

Guidelines:
- Use descriptive variable and function names
- Add comments for complex logic
- Follow the language's conventions and style guides
- Optimize for readability first, then performance
- Include type hints/annotations where applicable

When generating code:
- Provide complete, working implementations
- Include necessary imports
- Add docstrings and inline comments
- Consider security implications
- Handle errors gracefully"""

    async def generate_code(
        self,
        description: str,
        language: str,
        framework: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ADKResult:
        """Generate code based on description.
        
        Args:
            description: What to implement
            language: Programming language
            framework: Optional framework
            context: Additional context
            
        Returns:
            ADKResult with generated code
        """
        ctx = context or {}
        ctx["language"] = language
        if framework:
            ctx["framework"] = framework
        
        task = f"Implement the following in {language}"
        if framework:
            task += f" using {framework}"
        task += f":\n\n{description}"
        
        return await self.execute(task, ctx)
    
    async def refactor_code(
        self,
        code: str,
        instructions: str,
        language: str
    ) -> ADKResult:
        """Refactor existing code.
        
        Args:
            code: Code to refactor
            instructions: Refactoring instructions
            language: Programming language
            
        Returns:
            ADKResult with refactored code
        """
        task = f"""Refactor the following {language} code according to these instructions:

Instructions: {instructions}

Code:
```{language}
{code}
```

Provide the refactored code with explanations of changes made."""
        
        return await self.execute(task)


class CodeReviewADKAgent(ADKAgent):
    """Agent specialized in code review and analysis."""
    
    def get_agent_type(self) -> str:
        return "code_review"
    
    def get_system_prompt(self) -> str:
        return """You are an expert code reviewer with extensive experience in software quality and security.

Your review should cover:
1. **Code Quality**: Readability, maintainability, complexity
2. **Best Practices**: Language conventions, design patterns
3. **Bugs & Issues**: Logic errors, edge cases, potential crashes
4. **Security**: Vulnerabilities, input validation, data handling
5. **Performance**: Inefficiencies, resource usage, scalability
6. **Testing**: Test coverage, edge case handling

Review Format:
- Start with a brief summary
- List issues by severity (Critical, High, Medium, Low)
- Provide specific line references when possible
- Suggest concrete improvements with code examples
- End with an overall quality score (1-10)

Be constructive and specific. Focus on issues that matter most."""

    async def review_code(
        self,
        code: str,
        language: str,
        focus_areas: Optional[List[str]] = None
    ) -> ADKResult:
        """Review code for quality and issues.
        
        Args:
            code: Code to review
            language: Programming language
            focus_areas: Specific areas to focus on
            
        Returns:
            ADKResult with review feedback
        """
        task = f"Review the following {language} code:\n\n```{language}\n{code}\n```"
        
        context = {"language": language}
        if focus_areas:
            context["focus_areas"] = ", ".join(focus_areas)
            task += f"\n\nFocus especially on: {', '.join(focus_areas)}"
        
        return await self.execute(task, context)
    
    async def security_audit(
        self,
        code: str,
        language: str
    ) -> ADKResult:
        """Perform security-focused code audit.
        
        Args:
            code: Code to audit
            language: Programming language
            
        Returns:
            ADKResult with security findings
        """
        task = f"""Perform a security audit of the following {language} code.

Look for:
- Injection vulnerabilities (SQL, command, XSS)
- Authentication/authorization issues
- Sensitive data exposure
- Insecure cryptography
- Input validation problems
- Security misconfigurations

Code:
```{language}
{code}
```

Provide findings with severity levels and remediation steps."""
        
        return await self.execute(task, {"language": language, "focus": "security"})


class TestingADKAgent(ADKAgent):
    """Agent specialized in test generation and quality assurance."""
    
    def get_agent_type(self) -> str:
        return "testing"
    
    def get_system_prompt(self) -> str:
        return """You are an expert software tester specializing in comprehensive test coverage.

Your testing approach:
1. **Unit Tests**: Individual function/method testing
2. **Edge Cases**: Boundary conditions, null values, empty inputs
3. **Error Handling**: Exception cases, invalid inputs
4. **Integration**: Component interactions
5. **Performance**: Load and stress considerations

Test quality guidelines:
- Use descriptive test names that explain what's being tested
- Follow Arrange-Act-Assert (AAA) pattern
- Keep tests independent and isolated
- Mock external dependencies appropriately
- Aim for high code coverage but prioritize critical paths
- Include both positive and negative test cases

Use appropriate testing frameworks for the language (pytest, Jest, JUnit, etc.)."""

    async def generate_tests(
        self,
        code: str,
        language: str,
        framework: Optional[str] = None,
        test_types: Optional[List[str]] = None
    ) -> ADKResult:
        """Generate tests for code.
        
        Args:
            code: Code to test
            language: Programming language
            framework: Testing framework
            test_types: Types of tests to generate
            
        Returns:
            ADKResult with generated tests
        """
        task = f"Generate comprehensive tests for the following {language} code"
        
        if framework:
            task += f" using {framework}"
        
        if test_types:
            task += f"\n\nInclude these test types: {', '.join(test_types)}"
        
        task += f"\n\nCode:\n```{language}\n{code}\n```"
        
        context = {"language": language}
        if framework:
            context["framework"] = framework
        
        return await self.execute(task, context)
    
    async def suggest_edge_cases(
        self,
        function_signature: str,
        description: str
    ) -> ADKResult:
        """Suggest edge cases for testing.
        
        Args:
            function_signature: Function to analyze
            description: What the function does
            
        Returns:
            ADKResult with edge case suggestions
        """
        task = f"""Analyze this function and suggest edge cases for testing:

Function: {function_signature}
Description: {description}

List potential edge cases including:
- Boundary values
- Null/undefined inputs
- Empty collections
- Invalid types
- Concurrent access scenarios
- Resource exhaustion
- Error conditions"""
        
        return await self.execute(task)


class DocumentationADKAgent(ADKAgent):
    """Agent specialized in documentation generation."""
    
    def get_agent_type(self) -> str:
        return "documentation"
    
    def get_system_prompt(self) -> str:
        return """You are an expert technical writer creating clear, comprehensive documentation.

Documentation standards:
1. **Clarity**: Write for your audience, explain jargon
2. **Completeness**: Cover all necessary topics
3. **Examples**: Include practical code examples
4. **Structure**: Use clear headings and organization
5. **Accuracy**: Ensure technical correctness

Documentation types you create:
- API documentation with endpoints, parameters, responses
- README files with setup, usage, and examples
- Code comments and docstrings
- User guides and tutorials
- Architecture documentation

Format guidelines:
- Use proper Markdown formatting
- Include code blocks with syntax highlighting
- Add tables for structured information
- Use bullet points for lists
- Include diagrams descriptions where helpful"""

    async def generate_api_docs(
        self,
        code: str,
        language: str,
        format: str = "markdown"
    ) -> ADKResult:
        """Generate API documentation.
        
        Args:
            code: Code to document
            language: Programming language
            format: Output format
            
        Returns:
            ADKResult with API documentation
        """
        task = f"""Generate {format} API documentation for this {language} code:

```{language}
{code}
```

Include:
- Function/method signatures
- Parameter descriptions with types
- Return value descriptions
- Usage examples
- Error conditions"""
        
        return await self.execute(task, {"language": language, "format": format})
    
    async def generate_readme(
        self,
        project_info: Dict[str, Any]
    ) -> ADKResult:
        """Generate README file.
        
        Args:
            project_info: Project information dict
            
        Returns:
            ADKResult with README content
        """
        task = f"""Generate a comprehensive README.md for this project:

Project Name: {project_info.get('name', 'Unknown')}
Description: {project_info.get('description', 'No description')}
Language: {project_info.get('language', 'Unknown')}
Features: {', '.join(project_info.get('features', []))}

Include sections:
- Project title and badges
- Description
- Features
- Installation
- Quick start
- Usage examples
- Configuration
- Contributing
- License"""
        
        return await self.execute(task, project_info)


class ResearchADKAgent(ADKAgent):
    """Agent specialized in research and information synthesis."""
    
    def get_agent_type(self) -> str:
        return "research"
    
    def get_system_prompt(self) -> str:
        return """You are an expert researcher skilled at gathering, analyzing, and synthesizing information.

Research approach:
1. **Comprehensive**: Cover all relevant aspects
2. **Objective**: Present multiple viewpoints
3. **Evidence-based**: Support claims with reasoning
4. **Structured**: Organize findings clearly
5. **Actionable**: Provide practical recommendations

Research output format:
- Executive summary
- Key findings with supporting details
- Analysis and comparison
- Recommendations
- Limitations and caveats

Be thorough but concise. Distinguish between facts and opinions.
Acknowledge uncertainty where it exists."""

    async def research_topic(
        self,
        topic: str,
        depth: str = "comprehensive",
        aspects: Optional[List[str]] = None
    ) -> ADKResult:
        """Research a topic.
        
        Args:
            topic: Topic to research
            depth: Research depth (brief, comprehensive, exhaustive)
            aspects: Specific aspects to cover
            
        Returns:
            ADKResult with research findings
        """
        task = f"Research the following topic ({depth} analysis): {topic}"
        
        if aspects:
            task += f"\n\nFocus on these aspects: {', '.join(aspects)}"
        
        task += """

Provide:
1. Overview and background
2. Key findings
3. Different perspectives
4. Best practices or recommendations
5. Potential challenges or considerations"""
        
        return await self.execute(task, {"topic": topic, "depth": depth})
    
    async def compare_options(
        self,
        options: List[str],
        criteria: List[str],
        context: Optional[str] = None
    ) -> ADKResult:
        """Compare multiple options.
        
        Args:
            options: Options to compare
            criteria: Comparison criteria
            context: Additional context
            
        Returns:
            ADKResult with comparison analysis
        """
        task = f"""Compare these options: {', '.join(options)}

Criteria for comparison:
{chr(10).join(f'- {c}' for c in criteria)}"""
        
        if context:
            task += f"\n\nContext: {context}"
        
        task += """

Provide:
1. Brief overview of each option
2. Comparison table/matrix
3. Pros and cons of each
4. Recommendation with reasoning"""
        
        return await self.execute(task)
