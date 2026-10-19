<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture rules
- All backend calls go through `src/services/` (`GradeMatchService` interface, currently `MockService`); UI never calls fetch directly — so the real backend can be swapped in one place.
- The preview applies only the LUT returned by `renderLut`; never re-implement color adjustments in the UI — keeps preview and exported .cube identical.
