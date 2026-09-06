ADDON_DIR  := BlenderAddOn/binjo_addon
ADDON_SRC  := $(shell find $(ADDON_DIR) -type f \( -name '*.py' -o -name '*.toml' \))
ZIP_NAME   := BINjo_Kazooie.zip

MANIFEST   := $(ADDON_DIR)/blender_manifest.toml
INIT       := $(ADDON_DIR)/__init__.py
CHANGELOG  := CHANGELOG.md
VERSION    := $(shell sed -n 's/^version = "\([^"]*\)".*/\1/p' $(MANIFEST))

.PHONY: zip clean version bump bump-patch bump-minor bump-major \
        release-notes build-notes

zip: $(ZIP_NAME)

$(ZIP_NAME): $(ADDON_SRC)
	rm -f $(ZIP_NAME)
	cd BlenderAddOn && zip -r ../$(ZIP_NAME) binjo_addon \
		-x '*__pycache__*' -x '*.pyc'

clean:
	rm -f $(ZIP_NAME)

version:
	@echo $(VERSION)

# Bump the add-on version in the three places that carry it: the Blender
# manifest, the version_num stamped into exported materials, and the changelog
# (the [Unreleased] section is closed into a dated release).
#   make bump-patch / bump-minor / bump-major
#   make bump NEW_VERSION=1.2.3
bump-patch:
	@$(MAKE) --no-print-directory bump BUMP=patch

bump-minor:
	@$(MAKE) --no-print-directory bump BUMP=minor

bump-major:
	@$(MAKE) --no-print-directory bump BUMP=major

bump:
	@set -e; \
	cur='$(VERSION)'; \
	case "$$cur" in \
		[0-9]*.[0-9]*.[0-9]*) ;; \
		*) echo "cannot parse current version '$$cur' from $(MANIFEST)" >&2; exit 1 ;; \
	esac; \
	new='$(NEW_VERSION)'; \
	if [ -z "$$new" ]; then \
		major=$${cur%%.*}; rest=$${cur#*.}; minor=$${rest%%.*}; patch=$${rest#*.}; \
		case '$(BUMP)' in \
			major) major=$$((major + 1)); minor=0; patch=0 ;; \
			minor) minor=$$((minor + 1)); patch=0 ;; \
			patch|'') patch=$$((patch + 1)) ;; \
			*) echo "unknown BUMP='$(BUMP)' (use major, minor or patch)" >&2; exit 1 ;; \
		esac; \
		new="$$major.$$minor.$$patch"; \
	fi; \
	case "$$new" in \
		[0-9]*.[0-9]*.[0-9]*) ;; \
		*) echo "invalid target version '$$new'" >&2; exit 1 ;; \
	esac; \
	sed -i 's/^version = ".*"/version = "'"$$new"'"/' $(MANIFEST); \
	sed -i 's/^version_num = ".*"/version_num = "'"$$new"'"/' $(INIT); \
	grep -q '^version = "'"$$new"'"[[:space:]]*$$' $(MANIFEST); \
	grep -q '^version_num = "'"$$new"'"[[:space:]]*$$' $(INIT); \
	echo "version $$cur -> $$new"; \
	if [ ! -f $(CHANGELOG) ]; then \
		echo "warning: no $(CHANGELOG), skipping the changelog entry" >&2; \
	elif grep -q '^## \[Unreleased\]' $(CHANGELOG); then \
		if [ -z "$$($(MAKE) --no-print-directory release-notes V=Unreleased)" ]; then \
			echo "warning: [Unreleased] is empty, releasing $$new with no notes" >&2; \
		fi; \
		day=$$(date -u +%Y-%m-%d); \
		awk -v ver="$$new" -v day="$$day" \
			'{ print } \
			 !done && /^## \[Unreleased\]/ { print ""; print "## [" ver "] - " day; done = 1 }' \
			$(CHANGELOG) > $(CHANGELOG).tmp; \
		mv $(CHANGELOG).tmp $(CHANGELOG); \
		echo "$(CHANGELOG): [Unreleased] -> [$$new] - $$day"; \
	else \
		echo "warning: no '## [Unreleased]' heading in $(CHANGELOG)" >&2; \
	fi

# Print one changelog section as plain text, ready to paste into release notes.
# Defaults to the current version; `make release-notes V=Unreleased` also works.
release-notes:
	@ver='$(V)'; [ -n "$$ver" ] || ver='$(VERSION)'; \
	awk -v ver="$$ver" \
		'$$0 ~ "^## \\[" ver "\\]" { inside = 1; next } \
		 inside && /^## / { exit } \
		 inside { body = body $$0 "\n" } \
		 END { sub(/^\n+/, "", body); sub(/\n+$$/, "", body); if (body != "") print body }' \
		$(CHANGELOG)

# Commits landed since the version was last bumped — the "what is in this build
# but not in a release yet" list that CI attaches to every artifact.
build-notes:
	@base=$$(git log -1 --format=%H -G'^version = "' -- $(MANIFEST) 2>/dev/null); \
	if [ -z "$$base" ]; then \
		git log --format='- %s (%h)' -20; \
	else \
		git log --format='- %s (%h)' "$$base"..HEAD; \
	fi
