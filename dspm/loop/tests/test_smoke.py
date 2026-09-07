def test_loop_module_imports() -> None:
    from dspm.loop import auto_approve, issue_fix, monthly, watch

    assert callable(watch.watch)
    assert callable(monthly.generate_monthly)
    assert callable(auto_approve.should_auto_approve)
    assert callable(issue_fix.is_mechanical_issue)
