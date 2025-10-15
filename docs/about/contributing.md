Contributing to fakeredis
=========================

First off, thanks for taking the time to contribute! ❤️

All types of contributions are encouraged and valued.
See the table of contents for different ways to help and details about how this project handles
them. Please make sure to read the relevant section before making your contribution. It will make it a lot easier for
the maintainers and smooth out the experience for all involved. The community looks forward to your contributions. 🎉

> And if you like the project, but just don't have time to contribute, that's fine.
>
> There are other easy ways to support the project and show your appreciation, which we would also be very happy about:
>
> - Star the project
> - Tweet about it
> - Refer to this project in your project's readme
> - Mention the project at local meetups and tell your friends/colleagues

## Code of Conduct

This project and everyone participating in it is governed by the
[fakeredis Code of Conduct](https://github.com/cunla/fakeredis-py/blob/master/CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code. Please report unacceptable behavior
to <daniel@moransoftware.ca>.

## I Have a Question

> If you want to ask a question, we assume that you have read the
> available [Documentation](https://fakeredis.readthedocs.io/).

Before you ask a question, it is best to search for existing [Issues](https://github.com/cunla/fakeredis-py/issues) that
might help you. In case you have found a suitable issue and still need clarification, you can write your question in
this issue. It is also advisable to search the internet for answers first.

If you then still feel the need to ask a question and need clarification, we recommend the following:

- Open an [Issue](https://github.com/cunla/fakeredis-py/issues/new).
- Provide as much context as you can about what you're running into.
- Provide project and platform versions (nodejs, npm, etc), depending on what seems relevant.

We will then take care of the issue as soon as possible.

<!--
You might want to create a separate issue tag for questions and include it in this description.
People should then tag their issues accordingly.

Depending on how large the project is, you may want to outsource the questioning, e.g., to Stack Overflow or Gitter.
You may add additional contact and information possibilities:
- IRC
- Slack
- Gitter
- Stack Overflow tag
- Blog
- FAQ
- Roadmap
- E-Mail List
- Forum
-->

## I Want To Contribute

> ### Legal Notice <!-- omit in toc -->
> When contributing to this project, you must agree that you have authored 100% of the content, that you have the
> necessary rights to the content and that the content you contribute may be provided under the project license.

## Reporting Bugs

### Before Submitting a Bug Report

A good bug report shouldn't leave others needing to chase you up for more information.
Therefore, we ask you to investigate carefully, collect information and describe the issue in detail in your report.
Please complete the following steps in advance to help us fix any potential bug as fast as possible.

- Make sure that you are using the latest version.
- Determine if your bug is really a bug and not an error on your side, e.g., using incompatible
  environment components/versions (Make sure that you have read
  the [documentation](https://github.com/cunla/fakeredis-py).
  If you are looking for support, you might want to check [this section](#i-have-a-question)).
- To see if other users have experienced (and potentially already solved) the same issue you are having,
  check if there is not already a bug report existing for your bug or error in
  the [bug tracker](https://github.com/cunla/fakeredis-py/issues?q=label%3Abug).
- Also make sure to search the internet (including Stack Overflow) to see if users outside the GitHub
  community have discussed the issue.
- Collect information about the bug:
    - Stack trace (Traceback)
    - OS, Platform and Version (Windows, Linux, macOS, x86, ARM)
    - Version of the interpreter, compiler, SDK, runtime environment, package manager, depending on what seems relevant.
    - Possibly your input and the output
    - Can you reliably reproduce the issue? And can you also reproduce it with older versions?

### How Do I Submit a Good Bug Report?

> You must never report security related issues, vulnerabilities or bugs, including sensitive information
> to the issue tracker, or elsewhere in public.
> Instead, sensitive bugs must be sent by email to <daniel@moransoftware.ca>.

We use GitHub issues to track bugs and errors. If you run into an issue with the project:

- Open an [Issue](https://github.com/cunla/fakeredis-py/issues/new).
  (Since we can't be sure at this point whether it is a bug or not, we ask you not to talk about a bug yet and
  not to label the issue.)
- Follow the issue template and provide as much context as possible and describe the *reproduction steps* that someone
  else can follow to recreate the issue on their own.
  This usually includes your code.
  For good bug reports, you should isolate the problem and create a reduced test case.
- Provide the information you collected in the previous section.

Once it's filed:

- The project team will label the issue accordingly.
- A team member will try to reproduce the issue with your provided steps. If there are no reproduction steps or no
  obvious way to reproduce the issue, the team will ask you for those steps and mark the issue as `needs-repro`. Bugs
  with the `needs-repro` tag will not be addressed until they are reproduced.
- If the team is able to reproduce the issue, it will be marked `needs-fix`, as well as possibly other tags (such
  as `critical`), and the issue will be left to be [implemented by someone](#your-first-code-contribution).

<!-- You might want to create an issue template for bugs and errors that can be used as a guide and that defines the structure of the information to be included. If you do so, reference it here in the description. -->

## Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for fakeredis, **including completely new features
and minor improvements to existing functionality**. Following these guidelines will help maintainers and the community
to understand your suggestion and find related suggestions.

### Before Submitting an Enhancement

- Make sure that you are using the latest version.
- Read the [documentation](https://github.com/cunla/fakeredis-py) carefully and find out if the functionality is already
  covered, maybe by an individual configuration.
- Perform a [search](https://github.com/cunla/fakeredis-py/issues) to see if the enhancement has already been suggested.
  If it has, add a comment to the existing issue instead of opening a new one.
- Find out whether your idea fits with the scope and aims of the project. It's up to you to make a strong case to
  convince the project's developers of the merits of this feature. Keep in mind that we want features that will be
  useful to the majority of our users and not just a small subset. If you're just targeting a minority of users,
  consider writing an add-on/plugin library.

### How Do I Submit a Good Enhancement Suggestion?

Enhancement suggestions are tracked as [GitHub issues](https://github.com/cunla/fakeredis-py/issues).

- Use a **clear and descriptive title** for the issue to identify the suggestion.
- Provide a **step-by-step description of the suggested enhancement** in as many details as possible.
- **Describe the current behavior** and **explain which behavior you expected to see instead** and why. At this point
  you can also tell which alternatives do not work for you.
- You may want to **include screenshots and animated GIFs** which help you demonstrate the steps or point out the part
  which the suggestion is related to. You can use [this tool](https://www.cockos.com/licecap/) to record GIFs on macOS
  and Windows, and [this tool](https://github.com/colinkeenan/silentcast)
  or [this tool](https://github.com/GNOME/byzanz) on
  Linux. <!-- this should only be included if the project has a GUI -->
- **Explain why this enhancement would be useful** to most fakeredis users. You may also want to point out the other
  projects that solved it better and which could serve as inspiration.

<!-- You might want to create an issue template for enhancement suggestions that can be used as a guide and that defines the structure of the information to be included. If you do so, reference it here in the description. -->

## Your First Code Contribution

Unsure where to begin contributing? You can start by looking through
[help-wanted issues](https://github.com/cunla/fakeredis-py/labels/help%20wanted).

Never contributed to open source before? Here are a couple of friendly
tutorials:

- <http://makeapullrequest.com/>
- <http://www.firsttimersonly.com/>

### Getting started

- Create your own fork of the repository
- Do the changes in your fork
- Setup uv `pip install uv`
- Let uv install everything required for a local environment `uv sync`
- To run all tests, use: `uv run pytest -v`
- Note: In order to run the tests, a real redis server should be running.
  The tests are comparing the results of each command between fakeredis and a real redis.
    - You can use `docker-compose up redis6` or `docker-compose up redis7` to run redis.
- Run test with coverage using `uv run pytest -v --cov=fakeredis --cov-branch`
  and then you can run `coverage report`.

## Improving The Documentation

- Create your own fork of the repository.
- Do the changes in your fork, probably under the `docs/` folder.
- Create a pull request with the changes.

## Style guides

### Commit Messages

Taken from [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/)

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

The commit contains the following structural elements to communicate intent to the consumers of your library:

* `fix:` a commit of the type fix patches a bug in your codebase (this correlates with `PATCH` in Semantic Versioning).
* `feat:` a commit of the type feat introduces a new feature to the codebase (this correlates with `MINOR` in Semantic
  Versioning).
* `BREAKING CHANGE:` a commit that has a footer BREAKING CHANGE:, or appends a ! after the type/scope, introduces a
  breaking API change (correlating with MAJOR in Semantic Versioning). A BREAKING CHANGE can be part of commits of any
  type.
* types other than `fix:` and `feat:` are allowed, for example, `@commitlint/config-conventional` (based on the Angular
  convention) recommends `build:`, `chore:`, `ci:`, `docs:`, `style:`, `refactor:`, `perf:`, `test:`, and others.
* footers other than `BREAKING CHANGE: <description>` may be provided and follow a convention similar to
  [git trailer format](https://git-scm.com/docs/git-interpret-trailers).

Additional types are not mandated by the Conventional Commits specification, and have no implicit effect in Semantic
Versioning (unless they include a BREAKING CHANGE). A scope may be provided to a commit’s type, to provide additional
contextual information and is contained within parenthesis, e.g., feat(parser): add ability to parse arrays.

## Join The Project Team

If you wish to be added to the project team as a collaborator, please send
a message to daniel@moransoftware.ca with explanation.
